"""
AgentState — 在图中流动的唯一状态源。

每个节点都从此 TypedDict 读取和写入。字段保持精简；
只有当后续节点确实需要消费某个字段时，才会新增它。
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── 核心对话 ──────────────────────────────────────────────────────
    # add_messages reducer：新消息会*追加*（而非覆盖），
    # 相同 id 的消息则做幂等替换。
    messages: Annotated[list, add_messages]

    # ── Step 2: 意图识别与路由 ───────────────────────────────────────
    intent: str               # ORDER_QUERY / REFUND_RETURN / PRODUCT_KNOWLEDGE / CHITCHAT
    intent_confidence: float  # 0.0 – 1.0
    route: str                # 由 intent 推导出的目标节点名

    # ── Step 3: 工具调用与自我修正 ────────────────────────────────────
    correction_attempts: int  # 当前轮次工具调用循环的次数，路由节点会重置为 0
    escalation_reason: str | None  # 备用：非 None 表示需升级，由 local_rag_node 等节点写入

    # ── Step 4: 三层记忆管理 ──────────────────────────────────────────
    user_id: str                # 长期偏好的查询 key（当前为 mock 用户）
    turn_count: int             # 当前会话累计用户轮数
    session_summary: str        # 中期摘要，用于压缩较早对话
    user_preferences: dict      # 长期偏好（当前由 mock store 注入）
