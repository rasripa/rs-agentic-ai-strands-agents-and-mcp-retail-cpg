# Lab 8: AgentCore Policies

This lab demonstrates how to use Amazon Bedrock AgentCore Policy to enforce
security and safety controls at the gateway perimeter using boto3.

## Files (run in order)

| File | Description |
|------|-------------|
| `guardrails_in_policy.py` | **Part 1**: Create policy engine, attach to gateway, add guardrails + baseline permit |
| `policy_use_cases.py` | **Part 2**: Role-based tool access (Cognito JWT) + payload validation |
| `test_guardrails.py` | **Test**: Run a full test suite of safe/violent/hate/injection/PII inputs |
| `test_policies.py` | **Test**: Walkthrough of policy evaluation scenarios for each role |
| `test_gateway_invoke.py` | **Test**: Live gateway invocation to verify policy enforcement |

## Running

```bash
cd ~/agentic-ai-strands-agents-and-mcp-retail-cpg/lab-8/agentcore-policies

# Step 1: Create policy engine + guardrails
python guardrails_in_policy.py

# Step 2: Add role-based + payload policies
python policy_use_cases.py

# Step 3: Test guardrail detection
python test_guardrails.py

# Step 4: Understand policy evaluation logic
python test_policies.py

# Step 5: Test live gateway with policy enforcement
python test_gateway_invoke.py
```

## Prerequisites

- Completed Labs 1-5 (gateway deployed, SSM parameters stored)
- Python virtual environment activated
- boto3 installed
