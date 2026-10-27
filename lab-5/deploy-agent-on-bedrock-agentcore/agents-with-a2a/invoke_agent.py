import boto3
import json
from botocore.config import Config


def get_agent_arn_from_ssm(param_name: str) -> str:
    """Fetch agent ARN from SSM Parameter Store."""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=param_name)
    return response['Parameter']['Value']


# Initialize the AgentCore Runtime client with extended timeout
# Orchestrator calls multiple sub-agents sequentially (~100s total)
agent_core_client = boto3.client(
    'bedrock-agentcore',
    config=Config(read_timeout=300, connect_timeout=10)
)

# Fetch orchestrator agent ARN from SSM Parameter Store
agent_arn = get_agent_arn_from_ssm("orchestrator_agent_a2a_client_RuntimeArn")
prompt = "Hello, I am going to attend a party, and would like some suggestions for a midi dress that's available in stock. What can you recommend me? Also what are the AnyCompany return policies?"

# Prepare the payload
payload = json.dumps({"prompt": prompt}).encode()
session_id="1111111111111111aaaaaaaaaaaaaaaaabbbbbb"

print("agent_arn: ", agent_arn)
print("prompt: ", prompt)

# Invoke the agent
response = agent_core_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=session_id,
    payload=payload
)

response_body = response['response'].read()
response_data = json.loads(response_body)
print("Agent Response:", response_data)
