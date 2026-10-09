import asyncio
import os

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


REGION = "us-east-1"
GATEWAY_URL = (
    "https://helloagentv2-gateway-wxwoqd7hmx.gateway."
    "bedrock-agentcore.us-east-1.amazonaws.com/mcp"
)


class SigV4HTTPAuth(httpx.Auth):
    """Sign each outgoing HTTP request with AWS credentials."""

    def auth_flow(self, request):
        session = boto3.Session(region_name=REGION)
        credentials = session.get_credentials()

        if credentials is None:
            raise RuntimeError("No AWS credentials found.")

        frozen_credentials = credentials.get_frozen_credentials()

        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=dict(request.headers),
        )

        SigV4Auth(
            frozen_credentials,
            "bedrock-agentcore",
            REGION,
        ).add_auth(aws_request)

        for key, value in aws_request.headers.items():
            request.headers[key] = value

        yield request


async def main():
    print("Connecting to AgentCore Gateway...")

    async with httpx.AsyncClient(
        auth=SigV4HTTPAuth(),
        timeout=30.0,
    ) as http_client:
        async with streamable_http_client(
            GATEWAY_URL,
            http_client=http_client,
        #) as (read_stream, write_stream, _):
        ) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()

                print("MCP connection established.")
                print("Discovering available tools...")

                result = await session.list_tools()

                for tool in result.tools:
                    print(f"Tool: {tool.name}")
                    print(f"Description: {tool.description}")
                    #print(f"Input schema: {tool.inputSchema}")
                    print(f"Input schema: {tool.input_schema}")


                print("\nInvoking add_numbers through AgentCore Gateway...")

                result = await session.call_tool(
                    "HelloAgentV2-CalculatorTarget___add_numbers", arguments={"a": 173, "b": 289},
                )

                print(f"Tool execution result: {result.model_dump_json(indent=2)}")



if __name__ == "__main__":
    asyncio.run(main())
