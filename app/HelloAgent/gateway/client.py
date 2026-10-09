"""Strands MCP client for Amazon Bedrock AgentCore Gateway."""

import os
from contextlib import asynccontextmanager

import httpx
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

from gateway.auth import SigV4HTTPAuth


#DEFAULT_GATEWAY_URL = (
#    "https://helloagentv2-gateway-wxwoqd7hmx.gateway."
#    "bedrock-agentcore.us-east-1.amazonaws.com/mcp"
#)


def create_gateway_client() -> MCPClient:
    """Create a Strands MCP client authenticated with AWS IAM."""

    #gateway_url = os.environ.get(
    #    "AGENTCORE_GATEWAY_URL",
    #    DEFAULT_GATEWAY_URL,
    #)

    gateway_url = os.environ.get("AGENTCORE_GATEWAY_URL")

    if not gateway_url:
        raise RuntimeError(
            "AGENTCORE_GATEWAY_URL environment variable is required."
        )


    @asynccontextmanager
    async def transport():
        async with httpx.AsyncClient(
            auth=SigV4HTTPAuth(),
            timeout=30.0,
        ) as http_client:
            async with streamable_http_client(
                gateway_url,
                http_client=http_client,
            ) as streams:
                yield streams

    return MCPClient(transport)
