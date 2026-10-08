from collections import OrderedDict

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import (
    NullConversationManager,
)

from model.load import load_model


# AgentCore runtime application
app = BedrockAgentCoreApp()
log = app.logger


SYSTEM_PROMPT = """
You are a helpful assistant.
Use available tools when appropriate.
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b


TOOLS = [add_numbers]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

def create_agent() -> Agent:
    """Create a Strands agent backed by Amazon Bedrock."""
    return Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        conversation_manager=NullConversationManager(),
    )


# Keep a small in-process cache so a runtime session can reuse its agent.
# This is not durable AgentCore Memory and resets when the runtime restarts.
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


# ---------------------------------------------------------------------------
# AgentCore entrypoint
# ---------------------------------------------------------------------------

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
