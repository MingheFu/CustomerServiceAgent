"""
入口文件 — 端到端多 Agent 客服系统的交互式命令行（流式版本）。

流式架构:
    使用 LangGraph 的 `graph.stream(stream_mode=["updates", "messages"], subgraphs=True)`,
    单次调用同时获取两路事件流:
        - "updates"  → 节点级状态变更 (路由决策、工具调用、工具返回)
        - "messages" → token 级 LLM 输出, 用于打字机式流式打印

    通过 `langgraph_node` 元数据过滤, 仅把 chat / llm 这两类用户可见节点
    的 token 打印出来; router / 记忆摘要等中间节点的 token 不外泄。
    工具调用阶段 AIMessageChunk.content 通常为空 (参数走 tool_calls 字段),
    所以"先调用工具再回复文本"的多轮交互能自然地只把最终回复流式给用户。

用法:
    cp .env.example .env   # 填入你的 LLM_API_KEY
    pip install -r requirements.txt
    python main.py
"""

import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)

from src.config import Config
from src.graph import build_graph
from src.local_rag_path import ensure_local_rag_path
from src.tracing import AgentTracer


INTENT_LABELS = {
    "ORDER_QUERY": "📦 订单查询",
    "REFUND_RETURN": "↩️ 退换货售后",
    "PRODUCT_KNOWLEDGE": "💡 商品咨询",
    "PRIVATE_DOC_QUERY": "🔒 内部文档查询",
    "CHITCHAT": "💬 闲聊",
}

# 允许 token 流出的节点白名单。
#   - "chat"       : 主图的闲聊兜底节点
#   - "llm"        : 三个业务子图内部的 LLM 节点（最终面客回复也由它产出）
#   - "human_support": 明确转人工时创建工单后的最终回复
# 其余节点 (router / memory_context / memory_update / tools) 的 token
# 都不会流式打印, 防止把意图分类 JSON、摘要中间结果暴露给用户。
_STREAMABLE_NODES = {"chat", "llm", "human_support"}


# ---------------------------------------------------------------------------
# 单步事件打印辅助
# ---------------------------------------------------------------------------


def _print_router_decision(delta: dict) -> None:
    """路由节点完成时打印一行意图判定."""
    intent = delta.get("intent")
    if not intent:
        return
    label = INTENT_LABELS.get(intent, intent)
    conf = delta.get("intent_confidence", 0.0)
    print(f"[路由 → {label} | 置信度={conf:.2f}]", flush=True)


def _print_llm_tool_calls(delta: dict) -> None:
    """子图 LLM 节点产出 tool_calls 时, 提前预告即将执行的工具调用."""
    for msg in delta.get("messages", []) or []:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                args = tc.get("args", {}) or {}
                args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
                # 截断过长参数, 避免刷屏
                if len(args_str) > 100:
                    args_str = args_str[:97] + "..."
                print(f"[🔧 调用 {tc['name']}({args_str})]", flush=True)


def _print_tool_results(delta: dict) -> None:
    """工具节点返回 ToolMessage 时, 摘要打印 (含 Self-Correction 触发信号)."""
    for msg in delta.get("messages", []) or []:
        if not isinstance(msg, ToolMessage):
            continue
        first_line = str(msg.content).split("\n", 1)[0]
        # 突出展示 Self-Correction 触发点
        if first_line.startswith("❌ 工具入参"):
            print(f"[⚠️ {msg.name} 校验失败 → LLM 将自我修正] {first_line[:80]}", flush=True)
        else:
            preview = first_line[:80]
            ellipsis = "..." if len(first_line) > 80 else ""
            print(f"[✓ {msg.name} 返回] {preview}{ellipsis}", flush=True)


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------


def _check_escalation(state: dict) -> None:
    """检测本轮是否触发了 escalate_to_human 工具调用。"""
    for msg in reversed(list(state.get("messages", []))):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", "") == "escalate_to_human":
            content = str(getattr(msg, "content", ""))
            # 提取工单号
            for line in content.split("\n"):
                if "工单编号" in line:
                    print(f"\n📞 [HITL 触发] {line.strip()}", flush=True)
                    print("  客服专员将参考 AI 对话记录为您处理，请保持联系方式畅通。", flush=True)
            return


def run_cli() -> None:
    """启动交互式终端会话（流式输出）."""
    Config.validate()

    # Phase 3: 初始化本地 RAG 索引（嵌入模型加载后常驻 ~130MB）
    ensure_local_rag_path()
    from agent.rag_tool import build_rag_indexes
    from ingestion.pdf_parser import parse_and_chunk

    pdf_dir = Path(__file__).parent / "data"
    all_docs = []

    if pdf_dir.exists():
        for pdf_path in pdf_dir.glob("*.pdf"):
            chunk_dicts = parse_and_chunk(str(pdf_path))
            all_docs.extend([c["text"] for c in chunk_dicts])
            print(f"[RAG] 已加载 PDF: {pdf_path.name} ({len(chunk_dicts)} 个 chunk)")

    if all_docs:
        build_rag_indexes(all_docs)
        print(f"[RAG] 索引就绪，共 {len(all_docs)} 个 chunk")
    else:
        print("[RAG] 未找到 PDF 文件，跳过索引初始化（PRIVATE_DOC_QUERY 将不可用）")

    graph = build_graph()

    thread_id = str(uuid.uuid4())[:8]
    tracer = AgentTracer(thread_id, console=True)
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [tracer],
    }

    print("=" * 60)
    print("  Agent Customer Service  |  Streaming Mode")
    print(f"  模型: {Config.LLM_MODEL_ID}")
    print(f"  会话: {thread_id}")
    print("=" * 60)
    print("意图: ORDER_QUERY | REFUND_RETURN | PRODUCT_KNOWLEDGE | CHITCHAT")
    print('输入 "quit" 或 "exit" 退出。\n')

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("再见。")
            break

        agent_prefix_emitted = False
        tool_call_count = 0

        try:
            stream = graph.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                stream_mode=["updates", "messages"],
                subgraphs=True,
            )

            for chunk in stream:
                # subgraphs=True + 多模式: 每条 chunk 形如 (namespace, mode, payload)
                # namespace 是命名空间元组 (主图为空 tuple, 子图含 id)
                namespace, mode, payload = chunk

                if mode == "updates":
                    # payload: {node_name: state_delta_dict}
                    for node_name, delta in payload.items():
                        if not isinstance(delta, dict):
                            continue
                        if node_name == "router":
                            _print_router_decision(delta)
                        elif node_name == "llm":
                            # 在主图与各子图里, 业务子图内部的 LLM 节点都叫 "llm"
                            _print_llm_tool_calls(delta)
                        elif node_name == "tools":
                            _print_tool_results(delta)
                            # 每收到一次工具返回, 计数 +1 (用于轮次统计)
                            tool_call_count += sum(
                                1
                                for m in (delta.get("messages") or [])
                                if isinstance(m, ToolMessage)
                            )

                elif mode == "messages":
                    # payload: (AIMessageChunk, metadata_dict)
                    msg_chunk, meta = payload
                    if not isinstance(msg_chunk, AIMessageChunk):
                        continue
                    if meta.get("langgraph_node") not in _STREAMABLE_NODES:
                        continue
                    # tool-call 阶段 chunk.content 为空, 跳过即可,
                    # 这样多轮 Self-Correction 不会把中间幻觉文本流给用户
                    content = msg_chunk.content
                    if not content:
                        continue
                    if not agent_prefix_emitted:
                        print("Agent: ", end="", flush=True)
                        agent_prefix_emitted = True
                    sys.stdout.write(str(content))
                    sys.stdout.flush()

        except Exception as exc:
            print(f"\n[‼️ 流式异常] {type(exc).__name__}: {exc}", flush=True)

        # 收尾: 换行并打印本轮统计
        if agent_prefix_emitted:
            print()  # 结束流式行

        # 检测是否触发了转人工（流式结束后取最终 state 检查）
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            _check_escalation(final_state.values)

        stats_parts = []
        if tool_call_count:
            stats_parts.append(f"工具 {tool_call_count} 次")
        if stats_parts:
            print(f"[本轮 · {' | '.join(stats_parts)}]")
        print()


if __name__ == "__main__":
    run_cli()
