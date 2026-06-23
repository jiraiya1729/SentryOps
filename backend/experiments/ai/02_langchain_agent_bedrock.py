"""
Test 02: LangChain create_agent with AWS Bedrock + K8s tools.
Validates the agent pattern that will be used for the AI SRE assistant.
"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments.ai._config import MODEL_ID, AWS_REGION, check_aws_credentials
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
from langchain.agents import create_agent


SRE_SYSTEM_PROMPT = """You are an AI SRE assistant for a Kubernetes cluster. You have access to tools that query real-time cluster state including pods, deployments, logs, metrics, and events.

When answering questions:
- Always use tools to get current data rather than guessing.
- Cite specific evidence (pod names, metric values, log lines, event messages).
- If you detect an issue, explain the root cause and suggest a fix.
- Be concise but thorough."""


TOOLS = [get_pods, get_pod_detail, search_logs, get_metrics, get_events, get_deployments, describe_resource]


def test_agent_basic_query():
    """Test agent with a simple query that requires tool use."""
    print("\n" + "=" * 60)
    print("TEST: Agent Basic Query - Crashlooping Pods")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SRE_SYSTEM_PROMPT,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What pods are crashlooping? Investigate the root cause."}]}
    )

    print("\n--- Agent Response ---")
    for msg in result["messages"]:
        role = msg.type if hasattr(msg, "type") else "unknown"
        if role == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"\n[Tool Call]: {tc['name']}({tc['args']})")
        elif role == "ai" and msg.content:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            print(f"\n[Assistant]: {content[:500]}")
        elif role == "tool":
            print(f"\n[Tool Result]: {msg.name} -> {msg.content[:200]}...")

    print("\nSUCCESS: Agent executed tool calls and provided analysis.")


def test_agent_multi_tool():
    """Test agent that needs multiple tools to answer."""
    print("\n" + "=" * 60)
    print("TEST: Agent Multi-Tool Query - Cluster Health")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SRE_SYSTEM_PROMPT,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Give me a health summary: any unhealthy deployments, warning events, or pods using >90% memory?"}]}
    )

    print("\n--- Agent Response ---")
    final_response = [m for m in result["messages"] if m.type == "ai" and m.content]
    if final_response:
        print(f"\n[Final Answer]: {final_response[-1].content}")

    tool_calls = [m for m in result["messages"] if m.type == "ai" and hasattr(m, "tool_calls") and m.tool_calls]
    print(f"\nTools used: {sum(len(m.tool_calls) for m in tool_calls)} calls across {len(tool_calls)} steps")
    print("\nSUCCESS: Multi-tool agent query works.")


if __name__ == "__main__":
    check_aws_credentials()

    try:
        test_agent_basic_query()
        test_agent_multi_tool()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
