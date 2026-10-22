"""
端到端 Agent 评测执行器。

对 eval/cases.json 中的每条用例：
  1. 用独立 thread_id 调用 LangGraph（单轮用户输入）
  2. 从最终 state / messages 提取路由、工具链、最终回复
  3. 按规则打分（不依赖 LLM-as-judge，结果可复现、可 CI）

用法:
    python run_eval.py
    python run_eval.py --case order_lookup_valid
    python run_eval.py --tag order --skip-backend-check
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.config import Config
from src.graph import build_graph

CASES_PATH = Path(__file__).parent / "cases.json"
RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: int = 0


def load_cases(
    *,
    case_id: str | None = None,
    tag: str | None = None,
) -> list[dict]:
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = raw["cases"]
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            raise ValueError(f"未找到用例: {case_id}")
    if tag:
        cases = [c for c in cases if tag in c.get("tags", [])]
    return cases


def check_backend_ready() -> tuple[bool, str]:
    """探活 Java 后端（/api/health）。"""
    base = Config.BACKEND_URL.rstrip("/")
    url = f"{base}/health"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return True, url
        return False, f"{url} 返回 {resp.status_code}"
    except requests.RequestException as exc:
        return False, f"{url} 不可达: {exc}"


def _extract_artifacts(messages: list) -> dict[str, Any]:
    tools_called: list[str] = []
    lookup_order_count = 0
    tool_args: list[dict] = []

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "")
                tools_called.append(name)
                tool_args.append({"name": name, "args": tc.get("args") or {}})
                if name == "lookup_order":
                    lookup_order_count += 1

    escalated = any(
        isinstance(m, ToolMessage) and getattr(m, "name", "") == "escalate_to_human"
        for m in messages
    )

    final_answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            content = str(msg.content).strip()
            if content:
                final_answer = content
                break

    return {
        "tools_called": tools_called,
        "lookup_order_count": lookup_order_count,
        "tool_args": tool_args,
        "final_answer": final_answer,
        "escalated": escalated,
    }


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    for p in phrases:
        if p.lower() in lowered:
            return True
    return False


def _contains_none(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return all(p.lower() not in lowered for p in phrases)


def score_case(case: dict, state: dict, artifacts: dict) -> CaseResult:
    checks: dict[str, bool] = {}
    route = state.get("route") or state.get("intent") or ""
    tools = artifacts["tools_called"]
    answer = artifacts["final_answer"]

    # ── 路由 ──────────────────────────────────────────────────────────
    expected_route = case.get("expected_route")
    acceptable = case.get("acceptable_routes") or []
    if expected_route:
        ok_route = route == expected_route or route in acceptable
        checks["route"] = ok_route

    # ── 工具 ──────────────────────────────────────────────────────────
    for tool in case.get("expected_tools", []):
        checks[f"tool:{tool}"] = tool in tools

    for tool in case.get("forbidden_tools", []):
        checks[f"no_tool:{tool}"] = tool not in tools

    # acceptable_tools_extra：允许在 expected_tools 之外额外出现的工具，不替代主工具要求

    min_lookup = case.get("min_lookup_order_calls")
    if min_lookup is not None:
        checks["min_lookup_order_calls"] = artifacts["lookup_order_count"] >= min_lookup

    if case.get("require_escalation"):
        checks["escalation"] = artifacts["escalated"]

    # ── 最终回复 ──────────────────────────────────────────────────────
    if case.get("must_contain_any"):
        checks["must_contain_any"] = _contains_any(answer, case["must_contain_any"])

    if case.get("must_not_contain"):
        checks["must_not_contain"] = _contains_none(answer, case["must_not_contain"])

    if not answer and not case.get("require_escalation"):
        checks["has_final_answer"] = False
    elif answer:
        checks["has_final_answer"] = True

    # 无显式检查项时视为失败
    if not checks:
        checks["no_checks_defined"] = False

    passed = all(checks.values())
    return CaseResult(
        case_id=case["id"],
        passed=passed,
        checks=checks,
        detail={
            "route": route,
            "intent_confidence": state.get("intent_confidence"),
            "tools_called": tools,
            "lookup_order_count": artifacts["lookup_order_count"],
            "escalated": artifacts["escalated"],
            "final_answer_preview": answer[:400] if answer else "",
            "description": case.get("description", ""),
            "tags": case.get("tags", []),
        },
    )


def run_case(graph, case: dict) -> CaseResult:
    thread_id = f"eval-{case['id']}-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}
    t0 = time.time()

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=case["user_input"])]},
            config=config,
        )
    except Exception as exc:
        return CaseResult(
            case_id=case["id"],
            passed=False,
            error=f"{type(exc).__name__}: {exc}",
            latency_ms=round((time.time() - t0) * 1000),
        )

    messages = result.get("messages", [])
    artifacts = _extract_artifacts(messages)
    scored = score_case(case, result, artifacts)
    scored.latency_ms = round((time.time() - t0) * 1000)
    return scored


def run_suite(
    *,
    case_id: str | None = None,
    tag: str | None = None,
    skip_backend_check: bool = False,
) -> dict:
    Config.validate()
    cases = load_cases(case_id=case_id, tag=tag)

    backend_status = "skipped"
    if not skip_backend_check:
        ok, msg = check_backend_ready()
        if not ok:
            raise RuntimeError(
                f"Java 后端未就绪: {msg}\n"
                "请先启动 backend，或加 --skip-backend-check（仅测路由，业务工具会失败）。"
            )
        backend_status = msg

    graph = build_graph()
    results: list[CaseResult] = []

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']} … ", end="", flush=True)
        cr = run_case(graph, case)
        results.append(cr)
        icon = "✓" if cr.passed else "✗"
        print(f"{icon} ({cr.latency_ms}ms)")
        if not cr.passed:
            failed = [k for k, v in cr.checks.items() if not v]
            if failed:
                print(f"       未通过: {', '.join(failed)}")
            if cr.error:
                print(f"       错误: {cr.error}")

    passed = sum(1 for r in results if r.passed)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "backend": backend_status,
        "model": Config.LLM_MODEL_ID,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "cases": [
            {
                "id": r.case_id,
                "passed": r.passed,
                "checks": r.checks,
                "detail": r.detail,
                "error": r.error,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(out_path)
    return report


def print_summary(report: dict) -> None:
    print()
    print("=" * 60)
    print(f"  E2E Eval  {report['passed']}/{report['total']} passed "
          f"({report['pass_rate'] * 100:.0f}%)")
    print(f"  模型: {report['model']}")
    print(f"  报告: {report.get('report_path', '')}")
    print("=" * 60)
