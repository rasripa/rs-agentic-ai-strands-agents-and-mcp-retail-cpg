# Lab 5: Deploying agents to Amazon Bedrock AgentCore Runtime

Labs 0–4 ran agents locally. This lab deploys them to AgentCore Runtime, and does it **three
different ways** so the trade-offs between them are visible rather than asserted.

Each sub-directory is a complete, independent implementation of the same multi-agent system.
Deploy one, invoke it, then try another and compare what changed.

## The three topologies

### `agent-as-tools/`
The orchestrator holds the sub-agents **as tools**. Simplest to reason about and to deploy; the
orchestrator is coupled to its sub-agents, so adding one means changing orchestrator code.

- `FAQAgent.py`, `InventoryAgent.py`, `ProductSearchAgent.py` — the sub-agents
- `orchestrator-agent-agentcore.py` — the orchestrator
- `deploy-orchestrator-agent.py` — deploy
- `invoke_agent_as_tool_agent.py` — invoke

### `agent-invocation-with-boto3/`
Each agent is deployed as its **own AgentCore runtime**, and the orchestrator calls them over
boto3. Independently deployable and independently scalable; the orchestrator still needs to know
each runtime exists.

- `faq-agent-agentcore.py`, `inventory-agent-agentcore.py`, `product-search-agent-agentcore.py`
- `orchestrator-agent-boto3-agentcore.py`
- `deploy-all-agents.py` — deploys all four
- `invoke_agent_boto3.py`, `invoke_agent_utils.py`

### `agents-with-a2a/`
Agents expose themselves over the **A2A protocol** and advertise their skills through agent cards.
The orchestrator discovers capability rather than being told about it, so a new agent is a
deployment plus a registry entry — not an orchestrator change.

- `faq-agent-a2a-agentcore.py`, `inventory-agent-a2a-agentcore.py`,
  `product-search-agent-a2a-agentcore.py`
- `orchestrator-agent-with-a2a-client.py`
- `deploy-all-a2a-agents.py`, `deploy-orchestrator-agent-with-a2a-client.py`
- `invoke_a2a_agent.py`, `invoke_agent.py`

## Running a topology

```bash
cd <topology-directory>
pip install -r requirements.txt
python deploy-all-agents.py      # or the deploy script named in that directory
python invoke_agent_boto3.py     # or the matching invoke script
```

## Notes

- The agents bind `0.0.0.0` because AgentCore Runtime runs them in a managed container and reaches
  the process over the container network — nothing is published outside the runtime. Do not copy
  that bind into anything you run directly on a host.
- Deployment creates real AWS resources. Clean up when you're finished.
- Agents read configuration (knowledge base IDs, gateway tokens) from SSM Parameter Store, so the
  prerequisites and earlier labs must have run first.
