import os
import sys


MODEL_ID = "us.anthropic.claude-sonnet-4-6"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")


def check_aws_credentials() -> bool:
    key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not key or not secret:
        print("ERROR: AWS credentials not found in environment.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)
    print(f"AWS credentials found. Region: {AWS_REGION}")
    print(f"Model: {MODEL_ID}")
    return True


def check_langfuse_credentials() -> bool:
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        print("WARNING: Langfuse credentials not found. Tracing will be disabled.")
        print("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY for observability.")
        return False
    print(f"Langfuse configured. Host: {LANGFUSE_BASE_URL}")
    return True
