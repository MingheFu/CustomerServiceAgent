"""
Step 3 记忆管理辅助函数。

短期记忆由 LangGraph 的 MemorySaver 负责；本模块补充中期摘要与
mock 长期用户偏好，方便后续替换为 Redis / DB / 用户画像服务。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from src.state import AgentState

DEFAULT_USER_ID = "demo_user_001"
SUMMARY_EVERY_TURNS = 5
RECENT_VISIBLE_MESSAGES_TO_KEEP = 4


_MOCK_USER_PREFERENCES: dict[str, dict[str, Any]] = {
    DEFAULT_USER_ID: {
        "vip_level": 2,
        "frequent_buyer": True,
        "preferred_language": "zh-CN",
        "preferred_categories": ["机械键盘", "办公鼠标", "降噪耳机"],
        "budget_range": "500-1000",
        "tone_preference": "简洁、直接、少营销话术",
    }
}


def get_user_preferences(user_id: str) -> dict[str, Any]:
    """读取长期偏好；当前为 mock store，生产中可替换为 Redis / DB。"""
    return _MOCK_USER_PREFERENCES.get(user_id, {})


def format_memory_context(state: AgentState) -> str:
    """将摘要和长期偏好格式化为可注入 system prompt 的上下文。"""
    parts = []

    summary = state.get("session_summary")
    if summary:
        parts.append(f"【会话摘要】\n{summary}")

    preferences = state.get("user_preferences") or {}
    if preferences:
        pref_lines = [f"- {key}: {value}" for key, value in preferences.items()]
        parts.append("【用户长期偏好】\n" + "\n".join(pref_lines))

    if not parts:
        return ""

    return (
        "\n\n以下是可用于理解用户上下文的记忆信息。"
        "不要向用户暴露这些字段名，除非用户主动询问。\n"
        + "\n\n".join(parts)
    )


def should_summarize(turn_count: int) -> bool:
    """每 N 轮触发一次摘要，避免每轮都额外调用模型。"""
    return turn_count > 0 and turn_count % SUMMARY_EVERY_TURNS == 0


def select_recent_visible_messages(messages: list) -> list:
    """
    保留最近的用户/最终助手消息。

    Tool-calling 中间消息可能包含未展示给用户的工具请求与 ToolMessage。
    裁剪时只保留没有 tool_calls 的 HumanMessage / AIMessage，避免下轮
    请求出现 tool_call 与 ToolMessage 不配对的问题。
    """
    visible = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            visible.append(msg)
        elif isinstance(msg, AIMessage) and not msg.tool_calls and msg.content:
            visible.append(msg)
    return visible[-RECENT_VISIBLE_MESSAGES_TO_KEEP:]


def format_messages_for_summary(messages: list) -> str:
    """把消息压成摘要模型容易阅读的纯文本。"""
    lines = []
    for msg in messages:
        content = str(getattr(msg, "content", "")).strip()
        if not content:
            continue

        if isinstance(msg, HumanMessage):
            role = "用户"
        elif isinstance(msg, AIMessage):
            role = "客服"
        else:
            role = getattr(msg, "type", "消息")

        lines.append(f"{role}: {content}")

    return "\n".join(lines)
