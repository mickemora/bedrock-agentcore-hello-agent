import atexit

from collections import OrderedDict
from contextlib import ExitStack
from threading import Lock

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import (
    NullConversationManager,
)

from gateway.client import create_gateway_client
from model.load import load_model


app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT = """
You are a helpful assistant.
Use available tools when appropriate.
Use the calculator tool when asked to add numbers.
"""

# Gateway client lifecycle
_gateway_client = None
_gateway_lock = Lock()
_gateway_stack = ExitStack()

atexit.register(_gateway_stack.close)


def get_gateway_tools():
    """Connect to Gateway once and discover its MCP tools."""
    global _gateway_client

    with _gateway_lock:
        if _gateway_client is None:
            client = create_gateway_client()
            _gateway_stack.enter_context(client)
            _gateway_client = client
            log.info("Connected to AgentCore Gateway")

        return list(_gateway_client.list_tools_sync())


def create_agent() -> Agent:
    """Create a Strands agent using Gateway-backed tools."""
    return Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=get_gateway_tools(),
        conversation_manager=NullConversationManager(),
    )


_agents = OrderedDict()
_MAX_SESSIONS = 128


def get_agent(session_id: str) -> Agent:
    """Return the agent associated with a runtime session."""
    if session_id in _agents:
        _agents.move_to_end(session_id)
        return _agents[session_id]

    if len(_agents) >= _MAX_SESSIONS:
        _agents.popitem(last=False)

    agent = create_agent()
    _agents[session_id] = agent
    return agent


@app.entrypoint
async def invoke(payload, context):
    """Handle an AgentCore Runtime invocation."""
    log.info("Invoking HelloAgent")

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object.")

    prompt = payload.get("prompt", "")

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Payload must contain a non-empty 'prompt' string.")

    session_id = getattr(context, "session_id", "default-session")
    agent = get_agent(session_id)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue

        content_block_start = event["event"].get("contentBlockStart")

        if content_block_start is not None and not content_block_start.get("start"):
            continue

        yield event


if __name__ == "__main__":
    app.run()