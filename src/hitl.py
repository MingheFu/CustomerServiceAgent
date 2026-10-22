"""
Human-in-the-Loop (HITL) 兜底机制 — HTTP 适配层。

escalate_to_human 通过 POST /api/tickets 调用 Java 后端，
后端将工单写入 MySQL support_tickets 表。
"""

from __future__ import annotations

import json

import requests

from langchain_core.tools import tool

from src.config import Config


@tool
def escalate_to_human(
    issue_summary: str,
    attempted_solutions: str,
    urgency: str = "normal",
    preferred_contact: str = "",
) -> str:
    """
    当 AI 无法解决客户问题时，创建人工客服工单并升级。

    调用此工具的时机：
    - 自修正循环达到上限后仍无法给出有效回复
    - 客户明确要求转人工
    - 涉及敏感操作（大额退款、账户安全问题）
    - 置信度极低（< 0.5）且问题复杂

    参数:
        issue_summary: 问题摘要（客户诉求 + 关键信息如订单号、商品名）
        attempted_solutions: AI 已尝试的解决方案（工具调用记录等）
        urgency: 紧急程度，可选 "low" / "normal" / "high"
        preferred_contact: 客户偏好的联系方式（电话/邮件，可留空）
    """
    url = f"{Config.BACKEND_URL}/tickets"
    body = {
        "issueSummary": issue_summary,
        "attemptedSolutions": attempted_solutions,
        "urgency": urgency,
        "preferredContact": preferred_contact or "",
    }

    try:
        resp = requests.post(url, json=body, timeout=10)
    except requests.RequestException as exc:
        return (
            f"❌ 工单系统连接失败: {exc}。"
            "请告知客户稍后重试，或拨打客服热线 400-888-8888。"
        )

    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            return "❌ 工单创建失败，系统返回异常。请告知客户稍后重试或拨打客服热线。"
        hint = err.get("hint", "")
        hint_line = f"\n💡 {hint}" if hint else ""
        return f"❌ 工单创建失败: {err.get('message', str(err))}。{hint_line}"

    data = resp.json()
    message = data.get("message", "")
    ticket_id = data.get("ticketId", "?")
    contact_line = ""
    if preferred_contact:
        contact_line = f"  联系方式: {preferred_contact}\n"

    return (
        f"📋 人工客服工单已创建\n"
        f"  工单编号: {ticket_id}\n"
        f"  紧急程度: {urgency}\n"
        f"  问题摘要: {issue_summary}\n"
        f"  AI 已尝试: {attempted_solutions}\n"
        f"{contact_line}"
        f"  当前状态: 已分配客服专员，预计 30 分钟内通过电话/邮件回复\n"
        f"  ──────────────────\n"
        f"  {message or '客服专员将参考以上信息为您服务。'}\n"
        f"  感谢您的耐心等待！"
    )
