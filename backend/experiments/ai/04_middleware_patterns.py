"""
Test 04: LangChain/LangGraph middleware patterns for the SRE agent.
Demonstrates checkpointing, conversation memory, and custom callbacks.
"""

import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments.ai._config import MODEL_ID, AWS_REGION, check_aws_credentials
from experiments.ai.tools.k8s_tools import get_pods, get_events, get_metrics, get_pod_detail

from langchain_aws import ChatBedrockConverse
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver


class SREObservabilityCallback(BaseCallbackHandler):
    """Custom callback handler that logs agent behavior for SRE observability."""

    def __init__(self):
        self.tool_calls = []
        self.llm_calls = 0
        self.start_time = None
        self.total_tokens = 0

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs: Any) -> None:
        self.llm_calls += 1
        if self.start_time is None:
            self.start_time = time.time()
        print(f"  [SRE-OBS] LLM call #{self.llm_calls} started")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("usage", {})
            self.total_tokens += usage.get("total_tokens", 0)
        print(f"  [SRE-OBS] LLM call #{self.llm_calls} completed")

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "unknown")
        self.tool_calls.append({"name": tool_name, "input": input_str, "start": time.time()})
        print(f"  [SRE-OBS] Tool '{tool_name}' invoked")

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self.tool_calls:
            self.tool_calls[-1]["duration"] = time.time() - self.tool_calls[-1]["start"]
        output_str = str(output) if not isinstance(output, str) else output
        print(f"  [SRE-OBS] Tool completed ({len(output_str)} chars returned)")

    def summary(self) -> dict:
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            "total_time_seconds": round(elapsed, 2),
            "llm_calls": self.llm_calls,
            "tool_calls": len(self.tool_calls),
            "tools_used": [tc["name"] for tc in self.tool_calls],
            "total_tokens": self.total_tokens,
        }


def test_custom_callback():
    """Test custom SRE observability callback handler."""
    print("\n" + "=" * 60)
    print("TEST: Custom SRE Observability Callback")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=[get_pods, get_events, get_metrics, get_pod_detail],
        system_prompt="You are an AI SRE assistant. Use tools to investigate issues.",
    )

    sre_callback = SREObservabilityCallback()

    print("\nRunning agent with SRE observability callback...")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Investigate why payment-svc is unhealthy. Check pods, events, and logs."}]},
        config={"callbacks": [sre_callback]},
    )

    final = [m for m in result["messages"] if m.type == "ai" and m.content]
    if final:
        print(f"\n[Agent]: {final[-1].content[:300]}...")

    print("\n--- Observability Summary ---")
    summary = sre_callback.summary()
    for key, val in summary.items():
        print(f"  {key}: {val}")

    print("\nSUCCESS: Custom callback captures agent telemetry.")


def test_conversation_memory():
    """Test agent with conversation memory using checkpointer."""
    print("\n" + "=" * 60)
    print("TEST: Conversation Memory (Checkpointer)")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    checkpointer = MemorySaver()

    agent = create_agent(
        model=model,
        tools=[get_pods, get_events, get_metrics],
        system_prompt="You are an AI SRE assistant. Remember our conversation context.",
        checkpointer=checkpointer,
    )

    thread_config = {"configurable": {"thread_id": "sre-investigation-001"}}

    print("\n[Turn 1] User: What pods are crashlooping?")
    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "What pods are crashlooping?"}]},
        config=thread_config,
    )
    final1 = [m for m in result1["messages"] if m.type == "ai" and m.content]
    if final1:
        print(f"[Agent]: {final1[-1].content[:200]}...")

    print("\n[Turn 2] User: What are the metrics for that pod?")
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the memory metrics for that pod?"}]},
        config=thread_config,
    )
    final2 = [m for m in result2["messages"] if m.type == "ai" and m.content]
    if final2:
        print(f"[Agent]: {final2[-1].content[:200]}...")

    print("\n[Turn 3] User: Summarize the investigation")
    result3 = agent.invoke(
        {"messages": [{"role": "user", "content": "Summarize what we found in this investigation."}]},
        config=thread_config,
    )
    final3 = [m for m in result3["messages"] if m.type == "ai" and m.content]
    if final3:
        print(f"[Agent]: {final3[-1].content[:300]}...")

    print("\nSUCCESS: Conversation memory works across turns.")


def test_rate_limiting_callback():
    """Test a callback that tracks rate limiting and cost."""
    print("\n" + "=" * 60)
    print("TEST: Rate Limiting & Cost Tracking Callback")
    print("=" * 60)

    class CostTracker(BaseCallbackHandler):
        COST_PER_1K_INPUT = 0.003
        COST_PER_1K_OUTPUT = 0.015

        def __init__(self):
            self.calls = 0
            self.estimated_cost = 0.0

        def on_llm_end(self, response: Any, **kwargs: Any) -> None:
            self.calls += 1
            if hasattr(response, "llm_output") and response.llm_output:
                usage = response.llm_output.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                self.estimated_cost += (input_tokens / 1000) * self.COST_PER_1K_INPUT
                self.estimated_cost += (output_tokens / 1000) * self.COST_PER_1K_OUTPUT

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=[get_pods, get_metrics],
        system_prompt="You are an AI SRE assistant.",
    )

    cost_tracker = CostTracker()

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Show me pods with high memory usage."}]},
        config={"callbacks": [cost_tracker]},
    )

    print(f"\n  LLM calls made: {cost_tracker.calls}")
    print(f"  Estimated cost: ${cost_tracker.estimated_cost:.4f}")
    print("\nSUCCESS: Cost tracking callback works.")


def test_agent_middleware_class():
    """Test the LangChain v1 AgentMiddleware class (native middleware, not callbacks)."""
    print("\n" + "=" * 60)
    print("TEST: Native AgentMiddleware (LangChain v1)")
    print("=" * 60)

    from langchain.agents.middleware import AgentMiddleware

    class AuditMiddleware(AgentMiddleware):
        """Middleware that audits all model calls for compliance logging."""

        def __init__(self):
            self.model_calls = []
            self.tool_wraps = []

        def before_model(self, state, runtime):
            msg_count = len(state.get("messages", []))
            self.model_calls.append({"event": "before_model", "message_count": msg_count})
            print(f"  [AUDIT] Before model call ({msg_count} messages in context)")
            return None

        def after_model(self, state, runtime):
            self.model_calls.append({"event": "after_model"})
            print(f"  [AUDIT] After model call")
            return None

    audit = AuditMiddleware()

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=[get_pods, get_events],
        system_prompt="You are an AI SRE assistant.",
        middleware=[audit],
    )

    print("\nRunning agent with native AgentMiddleware...")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Any warning events?"}]}
    )

    final = [m for m in result["messages"] if m.type == "ai" and m.content]
    if final:
        content = final[-1].content if isinstance(final[-1].content, str) else str(final[-1].content)
        print(f"\n[Agent]: {content[:200]}...")

    print(f"\n  Middleware captured {len(audit.model_calls)} model lifecycle events")
    print("\nSUCCESS: Native AgentMiddleware works.")


if __name__ == "__main__":
    check_aws_credentials()

    try:
        test_custom_callback()
        test_conversation_memory()
        test_rate_limiting_callback()
        test_agent_middleware_class()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
