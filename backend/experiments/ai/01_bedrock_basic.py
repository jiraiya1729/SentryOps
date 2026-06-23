"""
Test 01: Basic AWS Bedrock connectivity with LangChain.
Validates that ChatBedrockConverse can connect and get a response from Claude Sonnet 4.6.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments.ai._config import MODEL_ID, AWS_REGION, check_aws_credentials

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage


def test_basic_invoke():
    """Test basic model invocation with ChatBedrockConverse."""
    print("\n" + "=" * 60)
    print("TEST: Basic Bedrock Invoke")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
    )

    messages = [
        SystemMessage(content="You are a helpful Kubernetes expert. Be concise."),
        HumanMessage(content="What is a Pod in Kubernetes? Answer in 2 sentences."),
    ]

    print(f"\nSending request to {MODEL_ID} in {AWS_REGION}...")
    response = model.invoke(messages)

    print(f"\nResponse type: {type(response).__name__}")
    print(f"Content: {response.content}")
    print(f"Usage metadata: {response.usage_metadata}")
    print("\nSUCCESS: Basic Bedrock invoke works.")


def test_streaming():
    """Test streaming response from Bedrock."""
    print("\n" + "=" * 60)
    print("TEST: Bedrock Streaming")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
    )

    messages = [HumanMessage(content="List 3 common Kubernetes issues in bullet points.")]

    print(f"\nStreaming from {MODEL_ID}...")
    print("Response: ", end="")

    for chunk in model.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)

    print("\n\nSUCCESS: Streaming works.")


def test_with_parameters():
    """Test model invocation with custom parameters."""
    print("\n" + "=" * 60)
    print("TEST: Bedrock with Custom Parameters")
    print("=" * 60)

    model = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.1,
        max_tokens=150,
    )

    messages = [HumanMessage(content="What causes OOMKilled in Kubernetes?")]

    print(f"\nSending with temperature=0.1, max_tokens=150...")
    response = model.invoke(messages)

    print(f"Content: {response.content}")
    print(f"Tokens used: {response.usage_metadata}")
    print("\nSUCCESS: Custom parameters work.")


if __name__ == "__main__":
    check_aws_credentials()

    try:
        test_basic_invoke()
        test_streaming()
        test_with_parameters()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        sys.exit(1)
