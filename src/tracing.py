"""
可观测性追踪 —— 基于 LangChain BaseCallbackHandler 的结构化执行日志。

自动捕获每次 LLM 调用、工具执行，写入 JSONL 日志文件。
同时可选终端摘要输出，方便调试。

面试要点：
    - 每条事件记录 timestamp 和 latency_ms，可以画时间线定位慢节点
    - on_tool_error 单独记录，与 on_llm_error 区分，精确定位故障层级
    - traces/ 目录按 session_id 分文件，支持并发会话
"""

from __future__ import annotations

import json
import time
import sys
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

TRACES_DIR = Path("traces")


class AgentTracer(BaseCallbackHandler):
    """
    结构化追踪回调。

    嵌入到 LangGraph 的 config["callbacks"] 即可自动工作。
    """

    def __init__(
        self,
        session_id: str,
        *,
        console: bool = False,  # 是否同步在终端打印摘要
    ):
        super().__init__()
        TRACES_DIR.mkdir(exist_ok=True)
        self.session_id = session_id
        self.trace_path = TRACES_DIR / f"{session_id}.jsonl"
        self.console = console
        self._timers: dict[str, float] = {}

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def on_llm_start(
        self, serialized: dict, prompts: list[str], **kwargs
    ) -> None:
        self._timers[_timer_key("llm", kwargs)] = time.time()

    def on_chat_model_start(
        self, serialized: dict, messages: list[list], **kwargs
    ) -> None:
        self._timers[_timer_key("llm", kwargs)] = time.time()

    def on_llm_end(self, response, **kwargs) -> None:
        run_id = _run_id(kwargs)
        latency_ms = _pop_latency(self._timers, _timer_key("llm", kwargs))
        usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
        elif hasattr(response, "usage_metadata"):
            usage = response.usage_metadata or {}

        self._emit({
            "type": "llm",
            "run_id": run_id,
            "latency_ms": latency_ms,
            "model": getattr(response, "model_name", "?"),
            "input_tokens": usage.get("input_tokens") or usage.get("prompt_tokens"),
            "output_tokens": usage.get("output_tokens") or usage.get("completion_tokens"),
        })

    def on_llm_error(self, error: BaseException, **kwargs) -> None:
        run_id = _run_id(kwargs)
        latency_ms = _pop_latency(self._timers, _timer_key("llm", kwargs))
        self._emit({
            "type": "llm_error",
            "run_id": run_id,
            "latency_ms": latency_ms,
            "error": f"{type(error).__name__}: {error}",
        })

    # ------------------------------------------------------------------
    # Tool
    # ------------------------------------------------------------------

    def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs
    ) -> None:
        self._timers[_timer_key("tool", kwargs)] = time.time()

    def on_tool_end(self, output: str, **kwargs) -> None:
        run_id = _run_id(kwargs)
        latency_ms = _pop_latency(self._timers, _timer_key("tool", kwargs))
        preview = str(output)[:120] if output else "(empty)"
        self._emit({
            "type": "tool",
            "run_id": run_id,
            "latency_ms": latency_ms,
            "preview": preview,
        })

    def on_tool_error(self, error: BaseException, **kwargs) -> None:
        run_id = _run_id(kwargs)
        latency_ms = _pop_latency(self._timers, _timer_key("tool", kwargs))
        self._emit({
            "type": "tool_error",
            "run_id": run_id,
            "latency_ms": latency_ms,
            "error": f"{type(error).__name__}: {error}",
        })

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _emit(self, event: dict) -> None:
        event["session"] = self.session_id
        event["timestamp"] = round(time.time(), 3)
        with open(self.trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        if self.console:
            type_icon = {
                "llm": "🤖",
                "llm_error": "🤖❌",
                "tool": "🔧",
                "tool_error": "🔧❌",
            }.get(event.get("type", ""), "•")
            latency = event.get("latency_ms", 0)
            extra = ""
            if event["type"] == "llm":
                extra = f" | in={event.get('input_tokens', '?')} out={event.get('output_tokens', '?')}tok"
            elif event["type"] == "tool":
                extra = f" | {event.get('preview', '')[:60]}"
            print(f"  [{type_icon} {event['type']} {latency:.0f}ms{extra}]", file=sys.stderr)


def _run_id(kwargs: dict) -> str:
    run_id = kwargs.get("run_id")
    return str(run_id) if run_id else "unknown"


def _timer_key(kind: str, kwargs: dict) -> str:
    run_id = _run_id(kwargs)
    # 现代 LangChain 回调都会传 run_id；unknown 仅作为旧版本兼容兜底。
    return f"{kind}:{run_id}"


def _pop_latency(timers: dict, key: str) -> int:
    start = timers.pop(key, None)
    if start is None:
        return -1
    return round((time.time() - start) * 1000)
