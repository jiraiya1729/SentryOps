"""
Test 03: Langfuse observability integration with LangChain agent.
Validates CallbackHandler tracing for the SRE agent.
"""

import sys
import os

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
from experiments.ai.tools.k8s_tools import get_pods, get_events, get_metrics

from langchain_aws import ChatBedrockConverse
from langchain.agents import create_agent


def test_langfuse_tracing():
    """Test Langfuse CallbackHandler with agent invocation."""
    print("\n" + "=" * 60)
    print("TEST: Langfuse Tracing Integration")
    print("=" * 60)

    from langfuse.callback import CallbackHandler

    langfuse_handler = CallbackHandler(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=[get_pods, get_events, get_metrics],
        system_prompt="You are an AI SRE assistant. Use tools to answer questions about the cluster.",
    )

    print("\nInvoking agent with Langfuse tracing enabled...")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Are there any warning events in the cluster?"}]},
        config={
            "callbacks": [langfuse_handler],
            "metadata": {
                "langfuse_user_id": "sre-operator-test",
                "langfuse_session_id": "poc-session-001",
                "langfuse_tags": ["poc", "sre-agent", "bedrock"],
            },
        },
    )

    final_msgs = [m for m in result["messages"] if m.type == "ai" and m.content]
    if final_msgs:
        print(f"\n[Agent Response]: {final_msgs[-1].content[:300]}...")

    langfuse_handler.flush()
    print("\nTraces flushed to Langfuse.")
    print(f"View traces at: {LANGFUSE_BASE_URL}")
    print("\nSUCCESS: Langfuse integration works.")


def test_langfuse_with_metadata():
    """Test passing custom metadata and session tracking."""
    print("\n" + "=" * 60)
    print("TEST: Langfuse with Custom Metadata")
    print("=" * 60)

    from langfuse.callback import CallbackHandler

    langfuse_handler = CallbackHandler(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )

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

    queries = [
        ("Which pods are using the most CPU?", "investigation-cpu-spike"),
        ("Are there any pods in pending state?", "investigation-scheduling"),
    ]

    for query, session_id in queries:
        print(f"\n  Query: {query}")
        print(f"  Session: {session_id}")

        result = agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config={
                "callbacks": [langfuse_handler],
                "metadata": {
                    "langfuse_user_id": "sre-operator-test",
                    "langfuse_session_id": session_id,
                    "langfuse_tags": ["poc", "batch-test"],
                },
                "run_name": f"sre-agent-{session_id}",
            },
        )

        final = [m for m in result["messages"] if m.type == "ai" and m.content]
        if final:
            print(f"  Response: {final[-1].content[:150]}...")

    langfuse_handler.flush()
    print("\nAll traces flushed.")
    print("\nSUCCESS: Metadata and session tracking works.")


if __name__ == "__main__":
    check_aws_credentials()
    has_langfuse = check_langfuse_credentials()

    if not has_langfuse:
        print("\nSkipping Langfuse tests (no credentials). Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
        print("The syntax is validated but traces won't be sent.")
        sys.exit(0)

    try:
        test_langfuse_tracing()
        test_langfuse_with_metadata()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
