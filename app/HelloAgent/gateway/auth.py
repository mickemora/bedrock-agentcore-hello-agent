"""AWS IAM authentication for AgentCore Gateway."""

import os

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class SigV4HTTPAuth(httpx.Auth):
    """Sign outgoing AgentCore Gateway requests using AWS SigV4."""

    def __init__(self, region=None):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.session = boto3.Session(region_name=self.region)

    def auth_flow(self, request):
        credentials = self.session.get_credentials()

        if credentials is None:
            raise RuntimeError("No AWS credentials available for Gateway.")

        frozen = credentials.get_frozen_credentials()

        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=dict(request.headers),
        )

        SigV4Auth(
            frozen,
            "bedrock-agentcore",
            self.region,
        ).add_auth(aws_request)

        for key, value in aws_request.headers.items():
            request.headers[key] = value

        yield request
