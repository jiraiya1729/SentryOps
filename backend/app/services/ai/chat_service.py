import logging
import time
from typing import AsyncGenerator

from langchain.agents import create_agent

from langchain.agents.middleware import AgentMiddleware
from langchain_aws import ChatBedrockConverse
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.services.ai.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """

You are an AI SRE assistant for a Kubernetes cluster. You have access to tools that query real-time cluster state: pods, deployments, logs, metrics, and events.

When answering questions:
- Always use tools to get current data rather than guessing.
- Cite specific evidence (pod names, metric values, log lines, event messages).
- If you detect an issue, explain the root cause and suggest a fix.
- Be concise but thorough. SREs are busy.
- Format responses with markdown for readability.
- When showing lists, use tables or bullet points.

You can make multiple tool calls if needed to fully answer a question.

"""

class SREObservabilityMiddleware(AgentMiddleware):
    
    def before_model(self, state, runtime):
        msg_count = len(state.get("messages", []))
        logger.info(f"Agent model call: {msg_count} messages in context.")
        return None

    def after_model(self, state, runtime):
        last_msg = state.get("message", [])[-1] if state.get("messages") else None
        tool_calls = len(getattr(last_msg, "tool_calls", [])) if last_msg else 0
        logger.info(f"Agent model response: {tool_calls} tool calls")
        return None

class TelemetryCallbackHandler(BaseCallbackHandler):

    def __init__(self):
        self.start_time = None
        self.llm_calls = 0
        self.tool_calls = []

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs: Any) -> None:

        if self.start_time is None:
            self.start_time = time.time()

        self.llm_calls += 1

    def on_tool_start(self, serialized: dict, prompts: list, **kwargs: Any) -> None:
        
        self.tool_calls.append(serialized.get("name", "unknown"))

    
    @property
    def duration(self) -> float:
        return time.time() - self.start_time if self.start_time else 0


class ChatService:
    
    def __init__(self):
        self.model = ChatBedrockConverse(
            model = settings.BEDROCK_MODEL_ID,
            region_name = settings.AWS_REGION,
            temperature = 0,
            max_tokens = 4096,
        )

        self.checkpointer = MemorySaver()
        self.langfuse_handler = self._init_langfuse()
        self.agent = create_agent(
            model = self.model,
            tools = ALL_TOOLS,
            system_prompt = SYSTEM_PROMPT,
            middleware = [SREObservabilityMiddleware],
            checkpointer = self.checkpointer,
        )

    
    def __init__langfuse(self):
        if not settings.LANGFUSE_PUBLIC_KEY:
            return None

        try:
            from langfuse.callback import CallbackHandler
            return CallbackHandler(
                public_key = settings.LANGFUSE_PUBLIC_KEY,
                secret_key = settings.LANGFUSE_SECRET_KEY,
                host = settings.LANGFUSE_BASE_URL,
            )
        except ImportError:
            logger.warning("langfuse not installed, tracing disabled")
            return None


    def _build_config(self, session_id: str, user_id: str | None = None) -> dict:
        config: dict[str, Any] = {
            "configurable": {"thread_id": session_id}
        }

        callbacks = []

        if self.langfuse_handler:
            callbacks.append(self.langfuse_handler)
        if callbacks:
            config["callbacks"] = callbacks
            config["metadata"] = {
                "langfuse_session_id": session_id,
                "langfuse_user_id": user_id or "anonymous",
                "langfuse_tags": ["sre-chat", "phase-3"],
            }
        return config

    
    async def chat(self, session_id: str, user_message: str) -> str:
        config = self._build_config(session_id)
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": "user_message"}]},
            config = config,
        )
        final = [m for m in result["messages"] if m.type == "ai" and m.content]
        if final:
            content = final[-1].content
            return content if isinstance(content, str) else str(content)
        return ""


    async def chat_stream(self, session_id: str, user_message: str) -> AsyncGenerator[dict, None]:
        config = self._build_config(session_id)

        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": user_message}]},
            config = config,
            version = "v2",
        ):
            kind = event.get("event")


            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        yield {"type":"token", "content": content}
                    
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                yield {"type": "token", "content": block["text"]}

            elif kind == "on_tool_start":
                yield {
                    "type": "tool_call",
                    "tool": event.get("name", ""),
                    "args": event.get("data", {}).get("input", {})
                }

            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                yield {
                    "type": "tool_result",
                    "tool": event.get("name", ""),
                    "summary": str(output)[:200],
                }

        yield {"type": "done"}


    def clear_session(self, session_id: str):
        pass


    async def get_session_history(self, session_id: str) -> list[dict]:
        config = {"configurable": {"thread_id": session_id}}
        state = self.agent.get_state(config)
        if not state or not state.values:
            return []

        history = []
        for msg in state.values.get("messages", []):
            if msg.type == "human":
                history.append({"role": "user", "content": msg.content})
            elif msg.type == "ai" and msg.content:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                history.append({"role": "assistant", "content": content})

        return history


chat_service = ChatService()
    