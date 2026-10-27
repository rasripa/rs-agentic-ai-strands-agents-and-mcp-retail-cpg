import boto3
import json
from uuid import uuid4

# Fetch the auto-generated agent card
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from urllib.parse import quote


def get_agent_arn_from_ssm(param_name: str) -> str:
    """Fetch agent ARN from SSM Parameter Store."""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=param_name)
    return response['Parameter']['Value']


# Fetch agent ARNs from SSM Parameter Store
faq_agent_arn = get_agent_arn_from_ssm("faq_agent_a2a_RuntimeArn")
product_search_agent_arn = get_agent_arn_from_ssm("product_search_agent_a2a_RuntimeArn")
inventory_agent_arn = get_agent_arn_from_ssm("inventory_agent_a2a_RuntimeArn")

# Test FAQ Agent with A2A protocol payload
agent_runtime_arn = faq_agent_arn
test_message = "Show me anycompany return policy"

# Test Product Search Agent with A2A protocol payload
#agent_runtime_arn = product_search_agent_arn
#test_message = "Could you recommend a men's jeans for me?"

# Test Inventory Agent with A2A protocol payload
#agent_runtime_arn = inventory_agent_arn
#test_message = "check availability of PROD-028"

# Test Orchestrator Agent with A2A protocol payload
# use invoke_agent.py to test orchestrator, as the orchestrator is not deployed as an A2A server

boto_session = boto3.Session()
region = boto_session.region_name
escaped_arn = quote(agent_runtime_arn, safe="")
agent_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_arn}/invocations"
print(f"Agent runtime URL: {agent_url}")
agent_card_url = f"{agent_url}/.well-known/agent-card.json"
credentials = boto_session.get_credentials()
request = AWSRequest(method="GET", url=agent_card_url)
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

response = requests.get(agent_card_url, headers=dict(request.headers))
agent_card = response.json()
print("Print the agent card :: ")
print(json.dumps(agent_card, indent=2))

print("Invoke the agent with input prompt :: ", test_message)
# A2A protocol uses JSON-RPC 2.0 format
payload = {
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": str(uuid4()),
    "params": {
        "message": {
            "messageId": str(uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": test_message}]
        }
    }
}

print("Testing Agent...")
print(f"Query: {test_message}")
print("-" * 60)

agent_core_client = boto3.client('bedrock-agentcore')

try:
    response = agent_core_client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        runtimeSessionId="1111111111111111aaaaaaaaaaaaaaaabbbbccccd",
        payload=json.dumps(payload).encode()
    )
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    result = response_data.get("result")
    # print("Agent Response - RAW :: ", result)
    final_response = ''
    if "artifacts" in result:
        for artifact in result["artifacts"]:
            for part in artifact.get("parts", []):
                if part.get("kind") == "text":
                    final_response=part["text"]
    print("Final Agent Response:", final_response)
except Exception as e:
    print(f"Error: {e}")
