import boto3
import json


def get_agent_arn_from_ssm(param_name: str) -> str:
    """Fetch agent ARN from SSM Parameter Store."""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=param_name)
    return response['Parameter']['Value']


# Initialize the AgentCore Runtime client
agent_core_client = boto3.client('bedrock-agentcore')

## Enable one of the prompts at a time to test the orchestrator agent
#prompt = "What is the returns policy of AnyCompany?"
prompt = "Could you recommend a men's jeans for me?"
#prompt = "Hello, I am going to attend a party, and would like some suggestions for a midi dress that's available in stock. What can you recommend me?"
#prompt="check availability of Levi's 501 Original Fit Jeans"

# Prepare the payload
payload = json.dumps({"prompt": prompt}).encode()

# Fetch orchestrator agent ARN from SSM Parameter Store
agent_arn = get_agent_arn_from_ssm("SearchOrchestratorAgentRuntimeArn")
# change the value of session_id to a >32 character unique value to track the request as a unique session
session_id="1111111111111111aaaaaaaaaaaaaaaaa"

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
