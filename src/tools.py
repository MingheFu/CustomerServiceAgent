"""
业务工具实现 — HTTP 适配层。

所有 @tool 函数通过 HTTP 调用 Java Spring Boot 后端。
函数签名、docstring 保持不变，方便 LLM 的 Function Calling 协议消费。

入参校验策略：
    order_id 客户端先做一次格式快检，避免无效请求浪费网络往返；
    其他参数由 Java 后端统一校验，错误通过 ErrorResponse 返回，
    本层解析后以"给 LLM 看"的格式透传wo s，支持 Self-Correction。
"""

from __future__ import annotations

import json

import requests

from langchain_core.tools import tool

from src.config import Config


# ═══════════════════════════════════════════════════════════════════════
# HTTP 调用辅助
# ═══════════════════════════════════════════════════════════════════════


def _call_backend(
    path: str,
    method: str = "GET",
    json_body: dict | None = None,
) -> dict:
    """
    调用 Java 后端并统一处理响应。

    成功 (2xx) → 返回 JSON dict
    失败 (4xx/5xx) → 从 ErrorResponse 中提取信息，组装"给 LLM 看"的错误字符串后
                    以 dict 形式抛给调用方（不抛异常，让 @tool 自行 return 给 LLM）
    """
    url = f"{Config.BACKEND_URL}{path}"
    try:
        resp = requests.request(
            method=method,
            url=url,
            json=json_body,
            timeout=10,
        )
    except requests.RequestException as exc:
        return {
            "_error": True,
            "content": f"❌ 后端连接失败: {type(exc).__name__}: {exc}。"
                       "请稍后重试，或调用 escalate_to_human 转人工。",
        }

    if resp.status_code < 300:
        return {"_error": False, "data": resp.json()}

    # 非 2xx → 解析 ErrorResponse
    try:
        err = resp.json()
    except Exception:
        return {
            "_error": True,
            "content": f"❌ 后端返回 {resp.status_code}，响应体无法解析。"
                       "请稍后重试或转人工。",
        }

    error_type = err.get("errorType", "SYSTEM_ERROR")
    message = err.get("message", str(err))
    hint = err.get("hint", "")

    hint_line = f"\n💡 修正建议: {hint}" if hint else ""

    if error_type == "VALIDATION_ERROR":
        return {
            "_error": True,
            "content": f"❌ 工具入参校验失败: {message}{hint_line}",
        }
    elif error_type == "NOT_FOUND":
        return {
            "_error": True,
            "content": f"❌ 资源不存在: {message}{hint_line}",
        }
    elif error_type == "BUSINESS_BLOCKED":
        return {
            "_error": True,
            "content": f"❌ 业务规则限制: {message}{hint_line}",
        }
    else:
        return {
            "_error": True,
            "content": f"❌ 系统错误: {message}。"
                       "建议向用户致歉并调用 escalate_to_human 转人工。",
        }


def _unwrap(result: dict) -> str:
    """从 _call_backend 的返回 dict 中提取字符串内容（给 LLM 看的格式）。"""
    if result.get("_error"):
        return result["content"]
    return json.dumps(result["data"], ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════════
# 订单域工具
# ═══════════════════════════════════════════════════════════════════════


@tool
def search_orders(query: str) -> str:
    """
    按商品名关键词搜索用户的订单。

    当用户不记得订单号、但记得买了什么商品时使用此工具。
    搜索命中后，从中提取 order_id 再调用 lookup_order 获取详情。

    参数:
        query: 商品名关键词，如"鼠标"、"键盘"、"耳机"等
    """
    return _unwrap(_call_backend(f"/orders/search?q={query}"))


@tool
def lookup_order(order_id: str) -> str:
    """
    根据订单号查询订单详情，包括状态、物流、商品信息。

    参数:
        order_id: 订单号，必须严格符合格式 YYYY-NNNNN（如 2024-78901）
    """
    return _unwrap(_call_backend(f"/orders/{order_id}"))


@tool
def modify_order_address(order_id: str, new_address: str) -> str:
    """
    修改未发货订单的收货地址。已发货的订单无法修改。

    参数:
        order_id: 订单号，必须严格符合格式 YYYY-NNNNN（如 2024-78901）
        new_address: 新的收货地址（完整地址，至少 6 个字符）
    """
    return _unwrap(_call_backend(
        f"/orders/{order_id}/address",
        method="PATCH",
        json_body={"newAddress": new_address},
    ))


# ═══════════════════════════════════════════════════════════════════════
# 售后域工具
# ═══════════════════════════════════════════════════════════════════════


@tool
def check_return_policy(product_category: str) -> str:
    """
    根据商品类别查询退换货政策（退货期限、条件、运费承担方）。

    参数:
        product_category: 商品类别，如"键盘"、"鼠标"、"耳机"、"显示器"、"笔记本"等
    """
    return _unwrap(_call_backend(f"/returns/policies/{product_category}"))


@tool
def create_return_request(order_id: str, reason: str) -> str:
    """
    为客户创建退货/退款工单。

    参数:
        order_id: 订单号，必须严格符合格式 YYYY-NNNNN（如 2024-78901）
        reason: 退货原因（质量问题/发错货/不想要了/其他）
    """
    return _unwrap(_call_backend(
        "/returns/requests",
        method="POST",
        json_body={"orderId": order_id, "reason": reason},
    ))


# ═══════════════════════════════════════════════════════════════════════
# 商品域工具
# ═══════════════════════════════════════════════════════════════════════


@tool
def search_product_specs(query: str) -> str:
    """
    根据关键词搜索商品参数和规格。

    参数:
        query: 搜索关键词，如"Keychron"、"MX Master"、"降噪耳机"等
    """
    return _unwrap(_call_backend(f"/products/search?q={query}"))


@tool
def get_product_recommendation(use_case: str, budget: str) -> str:
    """
    根据使用场景和预算推荐合适的商品。

    参数:
        use_case: 使用场景，如"办公"、"游戏"、"编程"、"音乐"、"日常"等
        budget: 预算范围，如"500以下"、"500-1000"、"1000-2000"、"不限"
    """
    return _unwrap(_call_backend(
        "/products/recommend",
        method="POST",
        json_body={"useCase": use_case, "budget": budget},
    ))
