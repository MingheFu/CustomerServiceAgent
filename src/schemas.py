"""
Pydantic 结构化输出模型。

与 state.py 分开管理，因为这些是面向模型的契约（schema），
而非图状态的字段定义。
"""

from pydantic import BaseModel, Field


class CustomerIntent(BaseModel):
    """路由 LLM 产出的结构化意图分类结果。"""

    intent: str = Field(
        description=(
            "分类后的客户意图。"
            "ORDER_QUERY: 查询或修改已有订单。"
            "REFUND_RETURN: 退换货、退款或售后投诉。"
            "PRODUCT_KNOWLEDGE: 商品规格、兼容性、推荐。"
            "PRIVATE_DOC_QUERY: 内部文档/知识库查询，如产品手册、FAQ、技术白皮书。"
            "CHITCHAT: 寒暄、闲聊、与业务无关的话题。"
        ),
        enum=["ORDER_QUERY", "REFUND_RETURN", "PRODUCT_KNOWLEDGE", "PRIVATE_DOC_QUERY", "CHITCHAT"],
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="分类置信度（0.0 – 1.0）。",
    )
    reasoning: str = Field(
        description="做出该分类的一句简短理由（中文）。",
    )
