"""
StateGraph 拓扑组装 —— 系统拓扑在此定义。

Step 3/4 拓扑结构（含记忆节点 + 工具调用子图）:

    START
      │
   memory_context_node  (加载长期偏好 / 恢复摘要)
      │
   router_node  (结构化意图分类)
      │
      ├── CHITCHAT ──────────→  chat_node ────────────→  memory_update_node ─→ END
      │
      ├── ORDER_QUERY ───────→  order_subgraph ───────→  memory_update_node ─→ END
      │     (LLM ↔ ToolNode 循环: lookup_order, modify_order_address)
      │
      ├── REFUND_RETURN ─────→  refund_subgraph ──────→  memory_update_node ─→ END
      │     (LLM ↔ ToolNode 循环: check_return_policy, create_return_request)
      │
      └── PRODUCT_KNOWLEDGE →  product_subgraph ──────→  memory_update_node ─→ END
            (LLM ↔ ToolNode 循环: search_product_specs, get_product_recommendation)
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from src.state import AgentState
from src.nodes import (
    memory_context_node,
    memory_update_node,
    router_node,
    chat_node,
    human_support_node,
    build_order_subgraph,
    build_refund_subgraph,
    build_product_subgraph,
    build_private_doc_subgraph,
)


def route_by_intent(state: AgentState) -> str:
    """条件边：将 intent 映射到下一个目标节点名。"""
    if _is_explicit_human_support_request(state):
        return "human_support"

    route = state.get("route", "CHITCHAT")
    mapping = {
        "CHITCHAT": "chat",
        "ORDER_QUERY": "order",
        "REFUND_RETURN": "refund",
        "PRODUCT_KNOWLEDGE": "product",
        "PRIVATE_DOC_QUERY": "private_doc",
    }
    return mapping.get(route, "chat")


def _is_explicit_human_support_request(state: AgentState) -> bool:
    """Detect explicit handoff requests without changing the router contract."""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) and msg.content:
            text = str(msg.content)
            return any(
                phrase in text
                for phrase in (
                    "转人工",
                    "人工客服",
                    "人工处理",
                    "真人客服",
                    "客服处理",
                    "人工专员",
                    "人工",
                    "agent"
                )
            )
    return False


def build_graph() -> StateGraph:
    """构造并编译 Agent StateGraph（含记忆节点与业务域子图）。"""
    builder = StateGraph(AgentState)

    # ── 注册节点 ──────────────────────────────────────────────────────
    builder.add_node("memory_context", memory_context_node)
    builder.add_node("router", router_node)
    builder.add_node("chat", chat_node)
    builder.add_node("human_support", human_support_node)
    # 三个业务域均为独立编译的子图（内部包含 tool-calling 循环）
    builder.add_node("order", build_order_subgraph())
    builder.add_node("refund", build_refund_subgraph())
    builder.add_node("product", build_product_subgraph())
    builder.add_node("private_doc", build_private_doc_subgraph())
    builder.add_node("memory_update", memory_update_node)

    # ── 连接拓扑 ──────────────────────────────────────────────────────
    builder.add_edge(START, "memory_context")
    builder.add_edge("memory_context", "router")
    builder.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "chat": "chat",
            "human_support": "human_support",
            "order": "order",
            "refund": "refund",
            "product": "product",
            "private_doc": "private_doc",
        },
    )
    # 所有业务叶子节点 → memory_update → END
    builder.add_edge("chat", "memory_update")
    builder.add_edge("human_support", "memory_update")
    builder.add_edge("order", "memory_update")
    builder.add_edge("refund", "memory_update")
    builder.add_edge("product", "memory_update")
    builder.add_edge("private_doc", "memory_update")
    builder.add_edge("memory_update", END)

    # ── 编译 ──────────────────────────────────────────────────────────
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
