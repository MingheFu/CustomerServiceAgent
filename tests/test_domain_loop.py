"""Offline regression tests: real LangGraph execution, scripted LLMs/tools.

Run: python -m unittest discover -s tests -v
No LLM credentials or Java backend are required.
"""

import importlib
import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool


class ScriptedModel:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def invoke(self, messages):
        if self.calls >= len(self.responses):
            raise AssertionError("Unexpected extra LLM call")
        response = self.responses[self.calls]
        self.calls += 1
        return response


def request(*names):
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": {}, "id": f"call_{i}_{name}"}
        for i, name in enumerate(names)
    ])


class DomainLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prevent construction of network clients at module import time.
        with patch("langchain_openai.ChatOpenAI", return_value=Mock()):
            cls.nodes = importlib.import_module("src.nodes")

    def setUp(self):
        self.business_calls = 0
        self.handoff_calls = 0
        self.fail_handoff = False

        @tool
        def business() -> str:
            """Return a simulated backend validation error."""
            self.business_calls += 1
            return "VALIDATION_ERROR: invalid parameter"

        @tool
        def escalate_to_human() -> str:
            """Create a simulated support ticket."""
            self.handoff_calls += 1
            if self.fail_handoff:
                raise RuntimeError("Simulated timeout")
            return "Ticket T-1 created"

        self.business = business
        self.handoff = escalate_to_human

    def run_graph(self, model, fallback):
        with patch.object(self.nodes, "escalate_to_human", self.handoff), \
             patch.object(self.nodes, "_escalation_llm", fallback):
            graph = self.nodes._build_domain_subgraph(
                model, [self.business, self.handoff], "Test domain"
            )
            return graph.invoke({
                "messages": [HumanMessage(content="Help")],
                "correction_attempts": 0,
            }, {"recursion_limit": 20})

    def test_normal_tool_result_returns_to_llm(self):
        model = ScriptedModel(request("business"), AIMessage(content="Please confirm"))
        result = self.run_graph(model, ScriptedModel())
        self.assertEqual(self.business_calls, 1)
        self.assertEqual(model.calls, 2)
        self.assertEqual(result["messages"][-1].content, "Please confirm")

    def test_handoff_is_terminal_even_before_budget(self):
        model = ScriptedModel(request("escalate_to_human"))
        result = self.run_graph(model, ScriptedModel())
        self.assertEqual(self.handoff_calls, 1)
        self.assertEqual(model.calls, 1)
        self.assertEqual(result["messages"][-1].content, "Ticket T-1 created")

    def test_retries_have_one_terminal_fallback(self):
        model = ScriptedModel(*[request("business") for _ in range(3)])
        fallback = ScriptedModel(request("escalate_to_human"))
        result = self.run_graph(model, fallback)
        self.assertEqual(self.business_calls, 3)
        self.assertEqual(self.handoff_calls, 1)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(result["correction_attempts"], 4)

    def test_parallel_handoffs_create_only_one_ticket_and_cancel_business(self):
        model = ScriptedModel(request("business", "escalate_to_human", "escalate_to_human"))
        result = self.run_graph(model, ScriptedModel())
        self.assertEqual(self.business_calls, 0)
        self.assertEqual(self.handoff_calls, 1)
        calls = result["messages"][1].tool_calls
        replies = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        self.assertEqual([m.tool_call_id for m in replies], [c["id"] for c in calls])

    def test_fallback_cannot_execute_business_tools(self):
        model = ScriptedModel(*[request("business") for _ in range(3)])
        result = self.run_graph(model, ScriptedModel(request("business")))
        self.assertEqual(self.business_calls, 3)
        self.assertEqual(self.handoff_calls, 0)
        self.assertFalse(result["messages"][-1].tool_calls)
        self.assertIn("上限", result["messages"][-1].content)

    def test_fallback_can_answer_without_ticket(self):
        model = ScriptedModel(*[request("business") for _ in range(3)])
        result = self.run_graph(model, ScriptedModel(AIMessage(content="Please confirm")))
        self.assertEqual(self.handoff_calls, 0)
        self.assertEqual(result["messages"][-1].content, "Please confirm")

    def test_handoff_exception_ends_without_retry_or_false_success(self):
        self.fail_handoff = True
        with self.assertLogs(self.nodes.logger, level="ERROR"):
            result = self.run_graph(
                ScriptedModel(request("escalate_to_human", "escalate_to_human")),
                ScriptedModel(),
            )
        self.assertEqual(self.handoff_calls, 1)
        self.assertIn("未能完成", result["messages"][-1].content)
        self.assertNotIn("T-1", result["messages"][-1].content)


if __name__ == "__main__":
    unittest.main()
