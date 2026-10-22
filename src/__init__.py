"""
Agent Customer Service — AI 核心大脑。

基于 LangGraph 的多 Agent 客服系统，面向 3C 数码/跨境电商场景，
分四个步骤逐步构建：

    Step 1  ✓  状态机骨架 + 基础对话通路
    Step 2  ✓  结构化意图识别 + 条件路由
    Step 3  ✓  三层记忆管理（短期 / 中期摘要 / 长期偏好）
    Step 4  ✓  工具调用闭环 + 自我修正

注意：长期偏好当前为 mock store，后续可替换为 Redis / DB。

所有公开 API 在包级别重新导出，方便调用方使用::

    from src import AgentState, build_graph, Config, CustomerIntent
"""

from src.config import Config
from src.schemas import CustomerIntent
from src.state import AgentState


def __getattr__(name: str):
    """Lazily expose build_graph without importing the full graph on package init."""
    if name == "build_graph":
        from src.graph import build_graph

        return build_graph
    raise AttributeError(f"module 'src' has no attribute {name!r}")

__all__ = ["AgentState", "CustomerIntent", "build_graph", "Config"]
