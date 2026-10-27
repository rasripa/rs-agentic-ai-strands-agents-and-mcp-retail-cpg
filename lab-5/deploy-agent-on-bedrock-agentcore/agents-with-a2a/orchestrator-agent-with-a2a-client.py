## Orchestrator agent that invokes sub-agents via A2A protocol on AgentCore Runtime.
#
# Uses A2AClientToolProvider from strands-agents-tools for automatic agent discovery
# and tool generation from Agent Cards. No manual tool wrappers needed.
#
# Pattern reference: strands-agents/samples
#   01-tutorials/03-deployment/04-multi-agent-agentcore-deployment/01-a2a-orchestration/03-a2a-client-orchestrator-agent.ipynb
##

from urllib.parse import quote
from typing import Generator

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands_tools.a2a_client import A2AClientToolProvider


# --- SigV4 Auth (matches reference: utils/sigv4_auth.py) ---

class SigV4HTTPXAuth(httpx.Auth):
    """Sign httpx requests with AWS SigV4 for AgentCore A2A calls.

    Connection header removal prevents SignatureDoesNotMatch errors.
    Fresh frozen credentials per request handle IAM role auto-refresh.
    """

    def __init__(self, credentials, service: str, region: str):
        self.credentials = credentials
        self.service = service
        self.region = region

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        headers = dict(request.headers)
        headers.pop("connection", None)
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )
        frozen_credentials = self.credentials.get_frozen_credentials()
        signer = SigV4Auth(frozen_credentials, self.service, self.region)
        signer.add_auth(aws_request)
        request.headers.update(dict(aws_request.headers))
        yield request


# --- Configuration ---

session = boto3.Session()
region = session.region_name or "us-west-2"
print(f"Using AWS region: {region}")

ssm_client = boto3.client('ssm', region_name=region)

try:
    faq_agent_arn = ssm_client.get_parameter(Name="faq_agent_a2a_RuntimeArn")['Parameter']['Value']
    product_search_agent_arn = ssm_client.get_parameter(Name="product_search_agent_a2a_RuntimeArn")['Parameter']['Value']
    inventory_agent_arn = ssm_client.get_parameter(Name="inventory_agent_a2a_RuntimeArn")['Parameter']['Value']
    print("✅ Sub-agent ARNs retrieved from SSM")

    agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
    print(f"Agent Model ID is {agent_model_id}")
except Exception as e:
    print(f"❌ Error retrieving sub-agent ARNs: {e}")
    raise


def build_agent_url(agent_arn: str) -> str:
    escaped_arn = quote(agent_arn, safe='')
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_arn}/invocations/"


faq_agent_url = build_agent_url(faq_agent_arn)
product_search_agent_url = build_agent_url(product_search_agent_arn)
inventory_agent_url = build_agent_url(inventory_agent_arn)

print(f"FAQ Agent URL: {faq_agent_url}")
print(f"Product Search Agent URL: {product_search_agent_url}")
print(f"Inventory Agent URL: {inventory_agent_url}")


# --- A2AClientToolProvider with SigV4 auth (matches reference pattern) ---

credentials = session.get_credentials()
auth = SigV4HTTPXAuth(credentials=credentials, service="bedrock-agentcore", region=region)

a2a_provider = A2AClientToolProvider(
    known_agent_urls=[faq_agent_url, product_search_agent_url, inventory_agent_url],
    httpx_client_args={"auth": auth},
)

print(f"A2AClientToolProvider initialized with {len(a2a_provider.tools)} tools")
for t in a2a_provider.tools:
    print(f"  → {t.tool_name}")


# --- Orchestrator Agent ---

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Search Orchestrator Agent, a sophisticated AI coordinator 
responsible for managing and directing queries to three specialized collaborator agents: the FAQ Agent, 
the Product Search Agent, and the Inventory Agent. Your primary role is to efficiently handle user 
inquiries by determining which agent(s) to engage and in what order.

Your key responsibilities include:
1. Analyze incoming user queries to understand their intent and requirements.
2. Decide which tool(s) to consult based on the nature of the query:
   - FAQ Agent Tool: For general questions about policies, procedures, or common inquiries. This tool does 
                     not have product or product availability related information.
   - Product Search Agent Tool: For queries related to finding specific products or product categories.
   - Inventory Agent Tool: For questions about stock levels and availability.
3. Determine the optimal sequence for consulting these tools if multiple tools are needed.
4. Formulate clear, concise sub-queries for each relevant tool.
5. Collect and synthesize responses from the collaborator tools.
6. Generate a comprehensive, coherent response for the user based on the information gathered.

Note:
1. Fetch product availability information only when explicitly asked by the customer. 
2. FAQ Agent Tool does not have product or product availability related information.

Remember, your goal is to provide accurate, helpful, and efficient responses to user queries by 
leveraging the specialized knowledge of each collaborator tool. Always strive for clarity, 
conciseness, and relevance in your communications with both users and collaborator tools.
"""

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60
)

bedrock_model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3,
    boto_client_config=boto_config,
)

print("Orchestrator agent configuration ready")


# --- Entrypoint ---

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke_agent(payload):
    """Invoke the orchestrator agent. Creates a new agent per request to avoid concurrency errors."""
    import traceback
    try:
        print(f"Received payload: {payload}", flush=True)
        user_input = payload.get("prompt")
        print(f"User input: {user_input}", flush=True)

        # New agent per request — Strands agents don't support concurrent invocations
        agent = Agent(
            name="Search_Orchestrator",
            description="Coordinates customer queries using FAQ, Product Search, and Inventory agents via A2A protocol",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            tools=a2a_provider.tools,
            model=bedrock_model,
        )

        response = agent(user_input)
        result = response.message['content'][0]['text']
        print(f"Response length: {len(result)}", flush=True)
        return result
    except Exception as e:
        print(f"❌ ERROR in invoke_agent: {e}", flush=True)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    app.run()
