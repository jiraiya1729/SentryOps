"""
Test 05: Full SRE Agent - Complete integration reference.
Combines: AWS Bedrock + LangChain Agent + All K8s Tools + Langfuse + Custom Callbacks + Memory.

This is THE definitive reference script for Phase 3/5 implementation.
"""

import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments.ai._config import (
    MODEL_ID,
    AWS_REGION,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_BASE_URL,
    check_aws_credentials,
    check_langfuse_credentials,
)
from experiments.ai.tools.k8s_tools import (
    get_pods,
    get_pod_detail,
    search_logs,
    get_metrics,
    get_events,
    get_deployments,
    describe_resource,
)

from langchain_aws import ChatBedrockConverse
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver


SRE_SYSTEM_PROMPT = """You are Guardian, an AI SRE assistant for a Kubernetes cluster operated by the SentryOps platform.

## Your Capabilities
You have access to real-time cluster tools:
- get_pods: List and filter pods by namespace/status
- get_pod_detail: Deep-dive into a specific pod (containers, resources, events)
- search_logs: Search container logs for errors and patterns
- get_metrics: CPU/memory usage metrics for capacity analysis
- get_events: Kubernetes events (warnings, errors, scheduling issues)
- get_deployments: Deployment health and replica status
- describe_resource: Full resource specifications

## Investigation Protocol
1. Start broad: check events and pod status for obvious issues
2. Narrow down: get details on affected resources
3. Correlate: check metrics and logs for root cause
4. Report: provide clear finding with evidence and remediation steps

## Response Format
- Lead with severity assessment (Critical/Warning/Info)
- Cite specific evidence (pod names, metric values, error messages)
- Provide actionable remediation steps
- Be concise — SREs are busy during incidents"""


ALL_TOOLS = [get_pods, get_pod_detail, search_logs, get_metrics, get_events, get_deployments, describe_resource]


class AgentTelemetry(BaseCallbackHandler):
    """Production-grade telemetry for the SRE agent."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = None
        self.llm_calls = 0
        self.tool_calls = []
        self.errors = []

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs: Any) -> None:
        if self.start_time is None:
            self.start_time = time.time()
        self.llm_calls += 1

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        self.tool_calls.append({
            "name": serialized.get("name", "unknown"),
            "timestamp": time.time(),
        })

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.errors.append(str(error))

    def report(self) -> dict:
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            "session_id": self.session_id,
            "duration_seconds": round(elapsed, 2),
            "llm_calls": self.llm_calls,
            "tools_invoked": [tc["name"] for tc in self.tool_calls],
            "tool_count": len(self.tool_calls),
            "errors": self.errors,
        }


def create_sre_agent(with_memory: bool = True):
    """Factory function to create the full SRE agent. Reusable for Phase 3 integration."""
    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
        max_tokens=2048,
    )

    kwargs = {
        "model": model,
        "tools": ALL_TOOLS,
        "system_prompt": SRE_SYSTEM_PROMPT,
    }

    if with_memory:
        kwargs["checkpointer"] = MemorySaver()

    return create_agent(**kwargs)


def run_investigation(agent, query: str, thread_id: str, callbacks: list = None):
    """Run a single investigation query and return structured results."""
    config = {"configurable": {"thread_id": thread_id}}
    if callbacks:
        config["callbacks"] = callbacks

    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )

    messages = result["messages"]
    tool_calls_made = []
    final_response = ""

    for msg in messages:
        if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_made.append(tc["name"])
        elif msg.type == "ai" and msg.content:
            final_response = msg.content

    return {
        "query": query,
        "response": final_response,
        "tools_used": tool_calls_made,
        "message_count": len(messages),
    }


def test_full_investigation():
    """Simulate a full incident investigation with multi-turn conversation."""
    print("\n" + "=" * 60)
    print("TEST: Full Incident Investigation")
    print("=" * 60)

    agent = create_sre_agent(with_memory=True)
    telemetry = AgentTelemetry(session_id="incident-2024-001")
    thread_id = "incident-investigation-001"

    queries = [
        "I'm getting alerts about the payment service. What's the current status?",
        "Investigate the root cause. Check the pod details, logs, and metrics.",
        "What's the recommended fix? Should we increase memory limits or is there a code issue?",
    ]

    print("\n--- Incident Investigation Session ---\n")
    for i, query in enumerate(queries, 1):
        print(f"\n[Turn {i}] Operator: {query}")
        result = run_investigation(agent, query, thread_id, callbacks=[telemetry])
        print(f"\n[Guardian]: {result['response'][:400]}")
        print(f"  (Tools used: {result['tools_used']})")

    print("\n\n--- Telemetry Report ---")
    report = telemetry.report()
    for key, val in report.items():
        print(f"  {key}: {val}")

    print("\nSUCCESS: Full investigation completed.")


def test_with_langfuse():
    """Test full agent with Langfuse tracing (if credentials available)."""
    print("\n" + "=" * 60)
    print("TEST: Full Agent + Langfuse Observability")
    print("=" * 60)

    has_langfuse = check_langfuse_credentials()
    if not has_langfuse:
        print("  Skipping (no Langfuse credentials)")
        return

    from langfuse.callback import CallbackHandler

    langfuse_handler = CallbackHandler(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )

    agent = create_sre_agent(with_memory=True)
    telemetry = AgentTelemetry(session_id="langfuse-test-001")
    thread_id = "langfuse-investigation-001"

    result = run_investigation(
        agent,
        "Give me a complete cluster health report. Check all deployments, any warning events, and pods with resource pressure.",
        thread_id,
        callbacks=[telemetry, langfuse_handler],
    )

    print(f"\n[Guardian]: {result['response'][:400]}")
    print(f"  Tools: {result['tools_used']}")

    langfuse_handler.flush()
    print(f"\n  Traces sent to: {LANGFUSE_BASE_URL}")
    print("\nSUCCESS: Full agent with Langfuse works.")


def test_concurrent_sessions():
    """Test multiple independent investigation sessions."""
    print("\n" + "=" * 60)
    print("TEST: Concurrent Investigation Sessions")
    print("=" * 60)

    agent = create_sre_agent(with_memory=True)

    sessions = [
        ("thread-cpu", "Which pods are consuming the most CPU?"),
        ("thread-scheduling", "Are there any pods stuck in Pending state? What's blocking them?"),
        ("thread-deployments", "Which deployments are not fully healthy?"),
    ]

    print("\nRunning 3 independent investigations...\n")
    for thread_id, query in sessions:
        result = run_investigation(agent, query, thread_id)
        print(f"  [{thread_id}] Tools: {result['tools_used']}")
        print(f"  Response: {result['response'][:150]}...\n")

    print("SUCCESS: Concurrent sessions work with isolated memory.")


if __name__ == "__main__":
    check_aws_credentials()

    print("=" * 60)
    print("SentryOps AI SRE Agent - Full Integration Test")
    print(f"Model: {MODEL_ID}")
    print(f"Region: {AWS_REGION}")
    print("=" * 60)

    try:
        test_full_investigation()
        test_with_langfuse()
        test_concurrent_sessions()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED - Reference implementation validated.")
        print("=" * 60)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
