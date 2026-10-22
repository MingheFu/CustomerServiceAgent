"""
图节点实现。

每个节点均为纯函数，签名为 (state) -> partial_state_update。
节点**绝不**原地修改 state —— 它们只返回变更字段的 dict。

Step 4 新增：三个业务域各有一个独立的 tool-calling 子图，
内部构成 LLM ↔ ToolNode 的自我修正循环。
"""

import logging
import re

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage

from src.config import Config
from src.schemas import CustomerIntent
from src.state import AgentState
from src.prompts import (
    ROUTER_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    ORDER_SYSTEM_PROMPT,
    REFUND_SYSTEM_PROMPT,
    PRODUCT_SYSTEM_PROMPT,
    PRIVATE_DOC_SYSTEM_PROMPT,
)
from src.tools import (
    search_orders,
    lookup_order,
    modify_order_address,
    check_return_policy,
    create_return_request,
    search_product_specs,
    get_product_recommendation,
)
from src.memory import (
    DEFAULT_USER_ID,
    format_memory_context,
    format_messages_for_summary,
    get_user_preferences,
    select_recent_visible_messages,
    should_summarize,
)
from src.hitl import escalate_to_human
from src.rag_tools import local_document_search

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MAX_CORRECTION_ATTEMPTS = 3  # 每轮最多允许 3 次工具调用迭代

# DeepSeek 默认启用 thinking mode，要求 reasoning_content 必须回传。
# LangChain 的 AIMessage 无法自动保留该字段，因此全局禁用 thinking。
_LLM_COMMON_KWARGS = {
    "api_key": Config.LLM_API_KEY,
    "base_url": Config.LLM_BASE_URL,
    "model": Config.LLM_MODEL_ID,
    "extra_body": {"thinking": {"type": "disabled"}},
}

# ---------------------------------------------------------------------------
# LLM 实例
# ---------------------------------------------------------------------------

# 对话模型 — 较高温度以获得更自然的回复。
_chat_llm = ChatOpenAI(
    **_LLM_COMMON_KWARGS,
    temperature=Config.TEMPERATURE,
    max_tokens=Config.MAX_TOKENS,
)

# 兜底模型 — 只绑 escalate_to_human，用于自修正超限后的 HITL 流程。
_escalation_llm = ChatOpenAI(
    **_LLM_COMMON_KWARGS,
    temperature=0.3,
    max_tokens=Config.MAX_TOKENS,
).bind_tools([escalate_to_human])

# 路由模型 — temperature=0，使用原生 Function Calling 进行意图分类。
# DeepSeek 不支持 with_structured_output 的 tool_choice 参数，
# 因此使用 bind_tools 走标准 OpenAI Function Calling 协议。
_router_llm = ChatOpenAI(
    **_LLM_COMMON_KWARGS,
    temperature=0.0,
    max_tokens=256,
).bind_tools([CustomerIntent])

# ---------------------------------------------------------------------------
# 路由 & 闲聊节点（主图直接使用）
# ---------------------------------------------------------------------------


def router_node(state: AgentState) -> dict:
    """
    对用户最新消息进行分类，将意图元数据写入 state。

    传给分类器的内容 = 最近 2 轮用户发言（不超过 300 字），
    保证分类器能理解当前消息所处的对话上下文，避免后续追问
    （如"那个鼠标 699 的"）被误判为商品咨询而非订单查询。
    同时重置 self-correction 计数器。
    """
    messages = state["messages"]
    if not messages:
        return _fallback_intent()

    # 收集最近至多 3 条用户消息作为上下文
    user_turns = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and msg.content:
            user_turns.append(msg.content.strip())
            if len(user_turns) >= 3:
                break
    user_turns.reverse()

    if not user_turns:
        return _fallback_intent()

    # 拼接上下文：当前消息 + 前一轮（如有）
    context = "\n".join(user_turns[-2:])  # 当前 + 最多 1 轮前
    if len(context) > 300:
        context = context[-300:]  # 截断过长内容

    try:
        classification = _classify(context)
        return {
            "intent": classification.intent,
            "intent_confidence": classification.confidence,
            "route": classification.intent,
            "correction_attempts": 0,  # 新轮次，重置计数器
        }
    except Exception as exc:
        logger.warning("意图分类失败: %s", exc)
        return _fallback_intent()


def chat_node(state: AgentState) -> dict:
    """通用对话节点 —— 处理闲聊或兜底回复。"""
    full_messages = [
        SystemMessage(content=_with_memory_context(CHAT_SYSTEM_PROMPT, state))
    ] + list(state["messages"])
    response: AIMessage = _chat_llm.invoke(full_messages)
    return {"messages": [response]}


def human_support_node(state: AgentState) -> dict:
    """用户明确要求转人工时，直接创建人工客服工单。"""
    latest_user_text = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) and msg.content:
            latest_user_text = str(msg.content).strip()
            break

    args = {
        "issue_summary": latest_user_text or "用户明确要求转人工客服处理",
        "attempted_solutions": "用户明确要求转人工，AI 未继续自动处理，直接创建人工客服工单。",
        "urgency": "normal",
        "preferred_contact": "",
    }
    tool_call_id = "call_escalate_to_human"
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "escalate_to_human",
                "args": args,
                "id": tool_call_id,
            }
        ],
    )
    tool_result = escalate_to_human.invoke(args)
    return {
        "messages": [
            tool_call,
            ToolMessage(
                content=str(tool_result),
                name="escalate_to_human",
                tool_call_id=tool_call_id,
            ),
            AIMessage(content=str(tool_result)),
        ]
    }


# ---------------------------------------------------------------------------
# 记忆节点（主图使用）
# ---------------------------------------------------------------------------


def memory_context_node(state: AgentState) -> dict:
    """
    注入长期偏好与记忆默认值。

    短期对话由 MemorySaver 自动恢复；这里补充 mock 长期偏好，
    并保证后续节点总能读到稳定的 memory 字段。
    """
    user_id = state.get("user_id") or DEFAULT_USER_ID
    preferences = state.get("user_preferences") or get_user_preferences(user_id)

    return {
        "user_id": user_id,
        "user_preferences": preferences,
        "session_summary": state.get("session_summary", ""),
        "turn_count": state.get("turn_count", 0),
    }


def memory_update_node(state: AgentState) -> dict:
    """
    每轮回复后更新中期摘要。

    每 SUMMARY_EVERY_TURNS 轮触发一次摘要，并用摘要 + 最近可见消息
    替代较早的完整消息历史，从而控制后续 prompt 长度。
    """
    turn_count = state.get("turn_count", 0) + 1
    updates = {"turn_count": turn_count}

    if not should_summarize(turn_count):
        return updates

    messages = list(state["messages"])
    summary = _summarize_session(
        previous_summary=state.get("session_summary", ""),
        messages=messages,
    )
    recent_messages = select_recent_visible_messages(messages)

    updates["session_summary"] = summary
    updates["messages"] = [
        RemoveMessage(id=REMOVE_ALL_MESSAGES),
        *recent_messages,
    ]
    return updates


# ═══════════════════════════════════════════════════════════════════════
# 业务域子图构建器（内部包含 LLM ↔ ToolNode 自我修正循环）
# ═══════════════════════════════════════════════════════════════════════


def build_order_subgraph() -> StateGraph:
    """构建订单域子图：LLM + 订单工具 + 自修正循环。"""
    tools = [search_orders, lookup_order, modify_order_address, escalate_to_human]
    llm = ChatOpenAI(
        **_LLM_COMMON_KWARGS,
        temperature=0.3,
        max_tokens=Config.MAX_TOKENS,
    ).bind_tools(tools)

    return _build_domain_subgraph(
        llm=llm,
        tools=tools,
        system_prompt=ORDER_SYSTEM_PROMPT,
    )


def build_refund_subgraph() -> StateGraph:
    """构建售后域子图：LLM + 退货工具 + 自修正循环。"""
    tools = [check_return_policy, create_return_request, escalate_to_human]
    llm = ChatOpenAI(
        **_LLM_COMMON_KWARGS,
        temperature=0.3,
        max_tokens=Config.MAX_TOKENS,
    ).bind_tools(tools)

    return _build_domain_subgraph(
        llm=llm,
        tools=tools,
        system_prompt=REFUND_SYSTEM_PROMPT,
    )


def build_product_subgraph() -> StateGraph:
    """构建商品域子图：LLM + 商品工具 + 自修正循环。"""
    tools = [search_product_specs, get_product_recommendation, escalate_to_human]
    llm = ChatOpenAI(
        **_LLM_COMMON_KWARGS,
        temperature=0.3,
        max_tokens=Config.MAX_TOKENS,
    ).bind_tools(tools)

    return _build_domain_subgraph(
        llm=llm,
        tools=tools,
        system_prompt=PRODUCT_SYSTEM_PROMPT,
    )


def build_private_doc_subgraph() -> StateGraph:
    """构建本地文档查询子图：LLM + local_document_search 工具 + 自修正循环。"""
    tools = [local_document_search, escalate_to_human]
    llm = ChatOpenAI(
        **_LLM_COMMON_KWARGS,
        temperature=0.3,
        max_tokens=Config.MAX_TOKENS,
    ).bind_tools(tools)

    return _build_domain_subgraph(
        llm=llm,
        tools=tools,
        system_prompt=PRIVATE_DOC_SYSTEM_PROMPT,
    )


# ═══════════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════════


def _build_domain_subgraph(
    llm: ChatOpenAI,
    tools: list,
    system_prompt: str,
) -> StateGraph:
    """
    通用的业务域子图工厂。

    拓扑结构:
        START → llm_node → [conditional]
                    │            ├── 有 tool_calls 且未超限 → tool_node → llm_node (循环)
                    │            └── 无 tool_calls 或超限 → END
                    │
                  tool_node (ToolNode 自动执行工具)

    自我修正机制:
        每次 LLM 调用都会递增 correction_attempts。
        达到 MAX_CORRECTION_ATTEMPTS 后强制终止循环，
        防止无限重试。
    """ 
    builder = StateGraph(AgentState)

    # 闭包：将 system_prompt 注入 LLM 调用。
    # 超限时自动切换为不带 tool 的 chat_llm，保证最终一定输出文本回复。
    def _llm_node(state: AgentState) -> dict:
        attempts = state.get("correction_attempts", 0)
        if attempts >= MAX_CORRECTION_ATTEMPTS:
            # HITL 兜底：只允许 escalate_to_human 一种 tool，防止继续调用业务工具
            override_prompt = (
                system_prompt
                + "\n\n【HITL 兜底】工具调用已达上限。你有两个选择：\n"
                "1. 如果已有足够信息 → 用纯文本直接回复客户\n"
                "2. 如果确实无法解决 → 调用 escalate_to_human 创建人工客服工单\n"
                "注意：你不可以再调用任何业务工具，只能选择 1 或 2。\n"
                '禁止输出任何 XML 标签。'
            )
            full = [
                SystemMessage(content=_with_memory_context(override_prompt, state))
            ] + list(state["messages"])
            response = _escalation_llm.invoke(full)
            # 防御性清洗
            response.content = _strip_tool_call_text(str(response.content))
        else:
            full = [
                SystemMessage(content=_with_memory_context(system_prompt, state))
            ] + list(state["messages"])
            response = llm.invoke(full)
        return {
            "messages": [response],
            "correction_attempts": attempts + 1,
        }

    builder.add_node("llm", _llm_node)
    builder.add_node("tools", ToolNode(tools + [escalate_to_human]))

    builder.add_edge(START, "llm")
    builder.add_conditional_edges(
        "llm",
        _should_continue_tools,
        {"tools": "tools", "end": END},
    )
    builder.add_edge("tools", "llm")

    return builder.compile()


def _should_continue_tools(state: AgentState) -> str:
    """条件边：判断是否继续工具调用循环。"""
    messages = state["messages"]
    if not messages:
        return "end"

    last_msg = messages[-1]

    # 有 tool_calls → 执行工具（llm_node 内部会在超限时强制终结）
    if last_msg.tool_calls:
        return "tools"

    return "end"


def _classify(user_text: str) -> CustomerIntent:
    """
    使用原生 Function Calling 进行意图分类。

    通过 bind_tools 将 CustomerIntent schema 绑定到 LLM，
    从返回的 AIMessage.tool_calls 中提取参数，再经 Pydantic 校验。
    若 LLM 未触发 tool_call（如对闲聊直接回复文本），则视为 CHITCHAT。
    """
    response = _router_llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ])
    if not response.tool_calls:
        # 模型未触发 function call，直接回了文本 → 视为闲聊
        return CustomerIntent(
            intent="CHITCHAT",
            confidence=0.8,
            reasoning="模型以文本回复，未触发函数调用，归类为闲聊",
        )
    args = response.tool_calls[0]["args"]
    return CustomerIntent.model_validate(args)


def _with_memory_context(system_prompt: str, state: AgentState) -> str:
    """将记忆上下文追加到业务 prompt 后。"""
    memory_context = format_memory_context(state)
    if not memory_context:
        return system_prompt
    return f"{system_prompt}\n\n{memory_context}"


def _summarize_session(previous_summary: str, messages: list) -> str:
    """使用普通 LLM 将当前会话压缩成中期摘要。"""
    transcript = format_messages_for_summary(messages)
    if not transcript:
        return previous_summary

    prompt = (
        "你是客服会话摘要器。请把对话压缩成便于后续客服继续服务的中文摘要。\n"
        "要求：保留用户目标、已确认事实、订单号/商品名/预算/偏好、未解决事项；"
        "不要添加对话中没有出现的信息；控制在 200 字以内。\n\n"
        f"已有摘要：{previous_summary or '无'}\n\n"
        f"本轮新增对话：\n{transcript}"
    )

    try:
        response = _chat_llm.invoke([HumanMessage(content=prompt)])
        return str(response.content).strip()
    except Exception as exc:
        logger.warning("会话摘要生成失败: %s", exc)
        return previous_summary


def _strip_tool_call_text(text: str) -> str:
    """
    清洗模型在无 tool binding 时产出的幻觉 tool_call 文本。

    DeepSeek 等模型可能在无工具绑定时仍输出 <tool_calls> XML 格式。
    检测到后截断并返回可读部分，若无有效内容则返回兜底文本。
    """
    if "<tool_calls>" not in text and "</tool_calls>" not in text:
        return text

    logger.debug("检测到幻觉 tool_call 文本，执行清洗")
    # 截取第一个 XML 标签之前的部分
    cleaned = re.split(r"<\s*/?\s*tool_calls", text)[0].strip()
    if cleaned:
        return cleaned
    return "抱歉，系统暂时无法完成该请求，请稍后重试或联系人工客服。"


def _fallback_intent() -> dict:
    """当分类无法完成时，返回安全的默认值（兜底为闲聊）。"""
    return {
        "intent": "CHITCHAT",
        "intent_confidence": 0.0,
        "route": "CHITCHAT",
        "correction_attempts": 0,
    }
