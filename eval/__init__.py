"""
端到端 Agent 评测包。

对 eval/cases.json 跑 LangGraph 单轮用例，规则打分，结果写入 eval/results/。

公开 API::

    from eval import run_suite, print_summary, load_cases, CaseResult
"""

from eval.runner import (
    CaseResult,
    check_backend_ready,
    load_cases,
    print_summary,
    run_case,
    run_suite,
    score_case,
)

__all__ = [
    "CaseResult",
    "check_backend_ready",
    "load_cases",
    "print_summary",
    "run_case",
    "run_suite",
    "score_case",
]
