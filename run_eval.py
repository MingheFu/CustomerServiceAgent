#!/usr/bin/env python3
"""
端到端 Agent 评测入口。

前置条件:
    1. .env 已配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID
    2. Java 后端已启动（默认 http://localhost:8080/api）
    3. MySQL seed 数据已加载（Flyway V2）

示例:
    python run_eval.py
    python run_eval.py --case order_self_correct_id
    python run_eval.py --tag refund
    python run_eval.py --skip-backend-check
"""

import argparse
import sys

from eval.runner import print_summary, run_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Customer Service E2E Eval")
    parser.add_argument("--case", help="只运行指定 case id")
    parser.add_argument("--tag", help="只运行带某 tag 的用例（order/refund/product/chitchat/hitl）")
    parser.add_argument(
        "--skip-backend-check",
        action="store_true",
        help="跳过 Java 健康检查（业务工具调用仍会失败）",
    )
    args = parser.parse_args()

    try:
        report = run_suite(
            case_id=args.case,
            tag=args.tag,
            skip_backend_check=args.skip_backend_check,
        )
    except Exception as exc:
        print(f"[eval 中止] {exc}", file=sys.stderr)
        return 1

    print_summary(report)
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
