# Amazon Bedrock AgentCore — Hello Agent

A deliberately minimal implementation of a **tool-using AI agent deployed on Amazon Bedrock AgentCore Runtime**.

The objective of this project is not to build a sophisticated application. It is to demonstrate, in the smallest practical example, the complete lifecycle of an AI agent:

**agent logic → model integration → tool selection → tool execution → local testing → AWS deployment → remote invocation**

---

## What This Demo Does

The agent accepts natural-language requests and uses **Claude Sonnet 4.5 through Amazon Bedrock** as its reasoning model.

It also has access to a custom Python tool:

```python
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b
```

When asked:

> Use your available tool to calculate 173 + 289.

the model determines that the `add_numbers` tool should be used, constructs the appropriate arguments, invokes the tool, observes the result, and generates the final response.

This demonstrates the fundamental agentic execution pattern:

```text
Reason
  ↓
Select Tool
  ↓
Construct Arguments
  ↓
Execute Tool
  ↓
Observe Result
  ↓
Respond
```

The calculator is intentionally trivial. The point of the demo is the **agent architecture and deployment lifecycle**, not the arithmetic.

---

## Architecture

```text
                       User / CLI
                           │
                           │ agentcore invoke
                           ▼
              ┌─────────────────────────┐
              │ Amazon Bedrock          │
              │ AgentCore Runtime       │
              │                         │
              │ BedrockAgentCoreApp     │
              │          │              │
              │          ▼              │
              │     Strands Agent       │
              │       /       \         │
              │      /         \        │
              │     ▼           ▼       │
              │ add_numbers    Model    │
              │   tool        request   │
              └─────────────────┼───────┘
                                │
                                ▼
                         Amazon Bedrock
                                │
                                ▼
                       Claude Sonnet 4.5
```

### Component Responsibilities

**Amazon Bedrock AgentCore Runtime**  
Provides the managed AWS runtime in which the agent executes.

**BedrockAgentCoreApp**  
Provides the runtime application harness and entrypoint used by AgentCore.

**Strands Agents SDK**  
Provides the agent framework responsible for orchestrating interactions between the model and available tools.

**Amazon Bedrock**  
Provides managed access to the foundation model using AWS identity and permissions.

**Claude Sonnet 4.5**  
Acts as the reasoning model that interprets requests and determines when an available tool should be used.

**Python Tool**  
`add_numbers` demonstrates how deterministic application capabilities can be exposed to the model.

---

## Project Structure

```text
.
├── README.md
├── .gitignore
├── app/
│   └── HelloAgent/
│       ├── main.py
│       ├── model/
│       │   └── load.py
│       ├── pyproject.toml
│       └── uv.lock
│
└── agentcore/
    ├── agentcore.json
    ├── aws-targets.example.json
    └── cdk/
```

Local deployment state, environment files, logs, caches, and AWS account-specific configuration are intentionally excluded from source control.

---

## Core Agent

The tool is intentionally simple:

```python
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b
```

It is supplied to a Strands agent:

```python
Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
    conversation_manager=NullConversationManager(),
)
```

The model is loaded from Amazon Bedrock:

```python
BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
```

No direct Anthropic API key is used by this implementation. Model access is performed through Amazon Bedrock using AWS credentials and IAM authorization.

---

## AgentCore Runtime Entrypoint

AgentCore invokes the application through the runtime entrypoint:

```python
@app.entrypoint
async def invoke(payload, context):
    ...
```

The entrypoint validates the incoming prompt, obtains the agent associated with the runtime session, passes the prompt to the Strands agent, and streams agent events back through the AgentCore runtime interface.

The small in-process agent cache is **not durable AgentCore Memory**. It is intentionally lightweight and can reset when the runtime process restarts.

---

## Tool-Use Flow

A request such as:

```text
Use your available tool to calculate 173 + 289.
```

produces the following conceptual flow:

```text
User Request
     │
     ▼
Claude Sonnet 4.5
     │
     │ decides a tool is appropriate
     ▼
add_numbers
     │
     │ a = 173
     │ b = 289
     ▼
Python Execution
     │
     ▼
462
     │
     ▼
Tool Result returned to model
     │
     ▼
Final natural-language response
```

During local testing, the AgentCore inspector showed the tool invocation with:

```json
{
  "a": 173,
  "b": 289
}
```

and the tool result:

```json
[
  {
    "text": "462"
  }
]
```

This is the important behavior demonstrated by the project: the model is not limited to generating text; it can select and invoke a controlled application capability.

---

## Prerequisites

To reproduce the demo, you will need:

- An AWS account
- AWS CLI configured with appropriate credentials
- Permission to use Amazon Bedrock and AgentCore resources required by the project
- Access to the configured Bedrock model
- Python
- Node.js / npm
- Amazon Bedrock AgentCore CLI

AWS permissions should follow least-privilege principles for real environments.

---

## Running Locally

From the project root:

```bash
agentcore dev
```

The local AgentCore development interface can then be used to interact with and inspect the agent.

A useful test prompt is:

```text
Use your available tool to calculate 173 + 289.
```

The expected result is:

```text
The sum of 173 + 289 is 462.
```

The inspector can also be used to verify that `add_numbers` was actually selected and executed.

---

## Configuring an AWS Deployment Target

The real `agentcore/aws-targets.json` is intentionally excluded from source control because it contains deployment-specific AWS account information.

Create it from the sanitized example:

```bash
cp agentcore/aws-targets.example.json agentcore/aws-targets.json
```

Then replace `<YOUR_AWS_ACCOUNT_ID>` with the AWS account ID for the environment in which you intend to deploy.

---

## Deploying to AWS

From the project root:

```bash
agentcore deploy
```

The project uses AWS CDK and CloudFormation as part of the deployment process.

Depending on the AWS environment, CDK may first require bootstrapping. Bootstrap infrastructure can include resources used to stage deployment assets, such as S3 and ECR resources and deployment roles.

---

## Invoking the Deployed Agent

After a successful deployment, invoke the agent remotely:

```bash
agentcore invoke "Explain what an API is in one sentence."
```

To demonstrate tool use:

```bash
agentcore invoke "Use your available tool to calculate 173 + 289."
```

Expected response:

```text
The sum of 173 + 289 is 462.
```

At this point the agent logic is executing in AWS rather than in the local development process.

---

## Skills Demonstrated

| Area | Demonstrated Capability |
|---|---|
| Agentic AI | Model-directed tool selection and execution |
| Amazon Bedrock AgentCore | Agent deployment and managed runtime execution |
| Strands Agents SDK | Agent orchestration and tool integration |
| Amazon Bedrock | Managed foundation-model inference |
| Claude | Natural-language reasoning and tool selection |
| Python | Agent logic and deterministic tool implementation |
| AWS IAM | Identity- and permission-based AWS access |
| AWS CDK | Infrastructure definition and deployment workflow |
| AWS CloudFormation | Infrastructure lifecycle management |
| Amazon ECR | CDK/deployment artifact infrastructure where applicable |
| Amazon S3 | CDK deployment artifact storage where applicable |
| AWS CLI | Authentication and AWS environment interaction |
| Observability / Debugging | Inspection of model and tool execution |
| Cloud Troubleshooting | Diagnosis of deployment and CDK bootstrap issues |

---

## Troubleshooting Experience From the Build

Building the demo also surfaced a useful real-world infrastructure scenario.

During deployment, the CDK bootstrap stack reported an ECR repository as an existing CloudFormation-managed resource even though the physical repository was no longer present. This caused AgentCore deployment to fail during CDK bootstrap.

The issue was isolated by comparing CloudFormation stack/resource state, the expected CDK bootstrap ECR repository, and the actual ECR registry state. The missing physical resource was restored and the deployment subsequently completed.

This reinforced an important cloud-engineering lesson:

> A successful infrastructure definition does not guarantee that the physical resources have remained consistent with the control-plane state. Deployment failures can require diagnosing infrastructure drift rather than changing application code.

---

## Why This Matters

The `add_numbers` function is deliberately trivial.

The important part is the architecture surrounding it.

The same pattern can expose enterprise capabilities such as:

```text
get_claim_status()
retrieve_policy()
check_vehicle_eligibility()
create_service_case()
query_inventory()
get_customer_history()
```

The architecture remains fundamentally similar:

```text
User Intent
     ↓
Foundation Model
     ↓
Tool Selection
     ↓
Controlled Enterprise Capability
     ↓
Result
     ↓
Model Response
```

This project therefore serves as a minimal reference implementation for understanding how an LLM moves from simply **generating text** to **reasoning over and invoking controlled application capabilities**.

---

## What This Demo Intentionally Does Not Include

To keep the architecture easy to understand, this version does not implement:

- AgentCore Memory
- AgentCore Gateway
- MCP tool servers
- Retrieval-Augmented Generation (RAG)
- Knowledge Bases
- Multi-agent orchestration
- AgentCore Browser
- AgentCore Code Interpreter
- Production end-user authentication flows
- Durable conversation history

These capabilities can be layered onto the same core architecture as requirements evolve.

---

## Security Notes

The deployed AgentCore Runtime is not intended to provide anonymous public access.

AWS authorization controls which principals can invoke deployed resources. Production implementations should apply least-privilege IAM permissions and appropriate authentication and authorization controls.

This repository intentionally excludes:

- AWS credentials
- local environment files
- AgentCore deployment state
- AWS account-specific target configuration
- local logs and caches
- the original local Git-history backup

Never commit AWS access keys, session credentials, tokens, or other secrets to source control.

---

## Cost Characteristics

This demo is designed as a small serverless learning workload.

The primary variable costs arise when the agent is invoked, including foundation-model inference and runtime consumption. Small amounts of storage may also be associated with deployment artifacts.

Actual AWS charges depend on region, usage, model pricing, runtime behavior, and the resources present in the AWS account. Consult current AWS pricing before using this architecture for sustained workloads.

---

## Key Takeaway

A useful mental model for the project is:

```text
Claude          = reasoning
Strands         = agent orchestration
Python tools    = capabilities
Bedrock         = managed model access
AgentCore       = managed agent runtime
CDK             = infrastructure deployment
```

Together, these components demonstrate the basic foundation of a tool-using agentic application on AWS.

---

## Next Evolution

A logical next step is replacing the calculator with a tool that retrieves information the model cannot know independently.

For example:

```python
@tool
def get_claim_status(claim_id: str) -> str:
    ...
```

That evolves the demo from:

**reason → calculate → respond**

to:

**reason → retrieve enterprise data → observe → respond**

This is the foundation for substantially more useful enterprise agents.
