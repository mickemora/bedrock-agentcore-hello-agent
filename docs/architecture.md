# Architecture — Amazon Bedrock AgentCore Hello Agent

## Purpose

This document explains the technical architecture of the Hello Agent demo. The implementation is intentionally small so the responsibilities of the model, agent framework, tool, application harness, and managed runtime remain easy to see.

## Architecture at a Glance

```text
User
 │
 ▼
AgentCore invocation
 │
 ▼
Amazon Bedrock AgentCore Runtime
 │
 ▼
BedrockAgentCoreApp
 │
 ▼
Strands Agent
 │
 ├──────────► Amazon Bedrock ──────────► Claude Sonnet 4.5
 │                                         │
 │                                         ▼
 │                                  Tool-use decision
 │                                         │
 ◄─────────────────────────────────────────┘
 │
 ▼
Python tool: add_numbers(a, b)
 │
 ▼
Tool result
 │
 ▼
Strands Agent → Claude → Final response
 │
 ▼
User
```

## Architectural Responsibilities

### Foundation Model — Reasoning

Claude Sonnet 4.5 is accessed through Amazon Bedrock. It interprets the request and can decide that an available tool should be invoked. The model generates the structured arguments for the tool; it does not execute the Python function itself.

```text
LLM = reasoning and tool-use decisions
```

### Strands Agent — Orchestration

The Strands Agents SDK coordinates the request, foundation model, registered tools, tool results, and subsequent model response.

```text
Strands = agent orchestration
```

### Python Tool — Controlled Capability

The demo exposes a deliberately simple capability:

```python
@tool
def add_numbers(a: int, b: int) -> int:
    return a + b
```

The arithmetic is not the architectural point. The important boundary is that the model decides whether to use a capability and supplies its arguments, while application code performs the deterministic operation.

The same pattern can represent enterprise capabilities such as:

```text
get_claim_status(claim_id)
retrieve_policy(policy_id)
check_vehicle_eligibility(vin)
query_inventory(part_number)
create_service_case(...)
```

```text
Tool = controlled capability available to the agent
```

### BedrockAgentCoreApp — Runtime Harness

The application creates `BedrockAgentCoreApp` and exposes an AgentCore entrypoint with `@app.entrypoint`.

This layer adapts the agent implementation to the AgentCore runtime contract. It receives an invocation, extracts the prompt, obtains the appropriate agent instance, executes the agent, and streams supported events to the caller.

```text
Harness = application adapter between agent logic and runtime
```

### AgentCore Runtime — Managed Execution

AgentCore Runtime is the AWS-managed environment in which the deployed application executes.

```text
Claude              = reasoning model
Strands             = agent framework / orchestration
BedrockAgentCoreApp = runtime-facing application harness
AgentCore Runtime   = managed execution environment
```

AgentCore does not replace the model or Strands. It provides infrastructure for running the agent application in AWS.

## End-to-End Tool Execution

Consider:

```text
Use your available tool to calculate 173 + 289.
```

The execution sequence is:

```text
1. Request reaches the AgentCore application entrypoint.
2. The prompt is passed to the Strands agent.
3. Strands supplies the request and tool definitions to Claude through Bedrock.
4. Claude determines that add_numbers is appropriate.
5. Claude generates arguments: a=173 and b=289.
6. Strands invokes the Python function.
7. The function returns 462.
8. The tool result becomes an observation in the agent loop.
9. Claude produces the final natural-language response.
10. AgentCore streams the response to the caller.
```

The observed tool arguments are equivalent to:

```json
{
  "a": 173,
  "b": 289
}
```

The important behavior is not the calculation itself. It is the model-directed invocation of a controlled external capability.

## Why This Is an Agent Rather Than Just an LLM Call

A basic LLM application commonly looks like:

```text
Prompt
  ↓
LLM
  ↓
Response
```

This project introduces an action loop:

```text
Prompt
  ↓
LLM
  ↓
Decision
  ↓
Tool
  ↓
Observation
  ↓
LLM
  ↓
Response
```

The model is therefore being used not only to generate text but also to participate in deciding when an external capability should be invoked and how that capability should be parameterized.

## Runtime and Model Are Separate Layers

Amazon Bedrock and Amazon Bedrock AgentCore serve different architectural roles:

```text
Amazon Bedrock
    └── Foundation-model access
         └── Claude Sonnet 4.5

Amazon Bedrock AgentCore
    └── Agent application infrastructure
         └── Runtime
```

This separation allows the reasoning model, orchestration logic, tools, and runtime infrastructure to evolve independently.

## Session Behavior

The application maintains a bounded in-process cache of agent instances keyed by session ID.

This is runtime-process state, not durable memory:

```text
in-process session state ≠ durable AgentCore Memory
```

It can be lost when the runtime process is replaced or restarted. A production conversational system requiring persistence should use an appropriate durable memory/session architecture.

## Deployment Architecture

The project was created with the AgentCore CLI and uses AWS CDK and CloudFormation as part of the deployment workflow.

```text
Source Code
    ↓
AgentCore CLI
    ↓
AWS CDK
    ↓
CloudFormation
    ↓
AWS Resources
    ↓
AgentCore Runtime
```

The demo uses a CodeZip-style deployment for the Python application. CDK bootstrap infrastructure can also provide supporting deployment resources.

## Security Boundary

The public source repository should contain application and infrastructure definitions, not AWS credentials.

Environment-specific and sensitive artifacts are excluded from version control, including local environment configuration, AgentCore CLI deployment state, and the real AWS target configuration.

A production architecture should additionally apply least-privilege IAM, caller authentication and authorization, tool-level authorization, input validation, auditability, appropriate data controls, and workload-specific network/security controls.

## Current Scope

V1 intentionally contains only the components required to demonstrate the core agent loop:

```text
Model
+
Agent Framework
+
Tool
+
Harness
+
Managed Runtime
```

It does not yet introduce durable AgentCore Memory, AgentCore Gateway, MCP servers, RAG, knowledge bases, multi-agent orchestration, browser automation, code execution tools, or a production end-user identity layer.

Keeping these concerns out of V1 makes the agent/tool/runtime relationship easier to understand.

## Enterprise Evolution

A meaningful next step is replacing the calculator with a capability that gives the model access to information it cannot know independently.

For example:

```python
@tool
def get_claim_status(claim_id: str) -> str:
    ...
```

The execution pattern becomes:

```text
User asks about a claim
        ↓
Claude interprets intent
        ↓
Agent selects get_claim_status
        ↓
Tool retrieves authoritative enterprise data
        ↓
Agent observes result
        ↓
Claude explains result
        ↓
User receives response
```

From there, the architecture can evolve toward:

```text
                    Enterprise Agent
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Memory           Gateway           RAG
          │                │                │
          ▼                ▼                ▼
     User context     APIs / MCP       Enterprise
                       / tools            data
```

## Architectural Takeaway

| Layer | Responsibility |
|---|---|
| Claude Sonnet 4.5 | Reason about the request and tool use |
| Amazon Bedrock | Provide managed model inference |
| Strands Agents SDK | Orchestrate the agent loop |
| Python tools | Execute controlled capabilities |
| BedrockAgentCoreApp | Adapt the application to AgentCore |
| AgentCore Runtime | Host and execute the deployed agent |
| CDK / CloudFormation | Provision and manage infrastructure |

The central design principle is separation of concerns:

> **Use the model for reasoning; use controlled tools for capabilities; use the agent framework for orchestration; and use the runtime for managed execution.**
