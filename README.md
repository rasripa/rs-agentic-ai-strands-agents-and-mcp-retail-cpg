> **A self-paced learning workshop.** Written for teaching rather than as a reference
> implementation or a deployable demo: the labs favour clarity over production hardening.
> All data is synthetic. Work through the labs in order, starting with `prereqs/`.
> The scripts default to **us-west-2** — set `AWS_REGION` if you work elsewhere.
>
> A personal project — not an official AWS project, and not supported by AWS.

## What this is, and what it isn't

This is **learning content**. The labs are meant to be read, run and broken — not cloned into a
project. Several things are deliberately simplified so the teaching point stays visible:

- IAM permissions are scoped for workshop convenience, not least privilege
- all data is synthetic; there is no customer or production data anywhere in this repository
- error handling, retries, timeouts and input validation are minimal
- local servers used in the labs have no authentication
- nothing here has been load-tested, cost-modelled, or security-reviewed for production use

If you want to take an idea from here into something real, treat the lab as the explanation and
write the production version yourself.

# Agentic AI with Strands Agents for Retail & CPG

This workshop demonstrates how to build intelligent AI agents for retail and consumer packaged goods (CPG) applications using Strands Agents and AWS services. Learn how to create specialized agents that can answer questions, search products, check inventory, and collaborate to solve complex customer queries.

## Workshop Structure

### Prerequisites
- Sample data for loading into S3 and DynamoDB.

### Lab 0: Fundamentals
Comprehensive introduction to Strands Agents framework:
- Basic agent creation and model configuration
- Tool integration and custom tool development
- Advanced patterns including async operations and callback handling
- Observability, monitoring, and debugging techniques
- Multi-modal capabilities and guardrail implementation

### Lab 1: FAQ Agents
Two approaches to building FAQ systems:
- **Lab 1a**: Console-based agent using Amazon Bedrock Agent Builder
- **Lab 1b**: Code-first approach with Strands Agents and Knowledge Base integration

### Lab 2: Product Search Agent
AI-powered shopping assistant Agent with advanced capabilities:
- Product discovery and recommendation engine
- Bedrock Knowledge Base integration for semantic search
- Content safety through guardrails implementation
- External service integration via MCP (Model Context Protocol)
- Product review aggregation and analysis

### Lab 3: Inventory Agent
Real-time inventory check Agent:
- Stock availability checking

### Lab 4: Search Orchestrator Agent
Multi-agent collaboration and intelligent routing:
- Centralized orchestration of specialized agents
- Intent recognition and query routing
- Agent coordination and response aggregation
- Scalable multi-agent architecture patterns

### Lab 5: Deploy Agents on Amazon Bedrock AgentCore
Deploy and run agents on AgentCore Runtime:
- **Agent-as-Tools**: Deploy the orchestrator with sub-agents as local tools on AgentCore
- **Agent Invocation with boto3**: Deploy individual agents on AgentCore and invoke sub-agents via boto3
- **Agents with A2A**: Deploy agents using the Agent-to-Agent (A2A) protocol for inter-agent communication

## Key Technologies

- **Amazon Bedrock**: Foundation models for natural language understanding
- **Strands Agents**: Code-first framework for building AI agents
- **Amazon Bedrock Knowledge Base**: Vector database for semantic search
- **Amazon Bedrock AgentCore**: Managed runtime for deploying and scaling agents
- **Amazon DynamoDB**: NoSQL database for product and inventory data
- **Model Context Protocol (MCP)**: Standard for agent-tool communication
- **Agent-to-Agent (A2A) Protocol**: Standard for inter-agent communication

## Model Configuration

- Lab 0 uses `us.anthropic.claude-haiku-4-5-20251001-v1:0` as the default model.
- Labs 1b through 5 retrieve the model ID from the SSM parameter `agent_model_id` at runtime, allowing you to switch models without code changes.
- The default value for `agent_model_id` is set to `us.anthropic.claude-haiku-4-5-20251001-v1:0` via the CloudFormation template.

## Getting Started

1. Deploy the CloudFormation stack from `static/cfn.yaml`
2. Start with `lab-0/fundamentals`
3. Progress through Labs 0-5 in sequence

## Requirements

- AWS account with access to Amazon Bedrock
- Python 3.11+
