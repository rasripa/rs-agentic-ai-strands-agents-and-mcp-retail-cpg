"""
Utility to invoke sub-agents on AgentCore Runtime via boto3.
"""

import boto3
import json


def get_agent_arn_from_ssm(param_name: str) -> str:
    """Fetch agent ARN from SSM Parameter Store."""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=param_name)
    return response['Parameter']['Value']


def invoke_agent_with_boto3(agent_arn: str, user_query: str) -> str:
    """
    Invoke a sub-agent deployed on AgentCore Runtime using boto3.

    Args:
        agent_arn: The ARN of the AgentCore Runtime to invoke.
        user_query: The user's query to send to the sub-agent.

    Returns:
        The agent's response as a string.
    """
    agentcore_client = boto3.client('bedrock-agentcore')

    print(f"Invoking agent: {agent_arn}")
    print(f"query: {user_query}")
    boto3_response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": user_query})
    )

    if "text/event-stream" in boto3_response.get("contentType", ""):
        # Handle streaming response
        result = ""
        for line in boto3_response["response"].iter_lines(chunk_size=1):
            if line:
                line = line.decode("utf-8")
                line = line[6:]  # Strip "data: " prefix
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                line = line.replace('\\n', '\n')
                result += line
    else:
        # Handle non-streaming response
        response_body = boto3_response['response'].read()
        response_data = json.loads(response_body)
        result = response_data

    return result


# Fetch agent ARNs from SSM Parameter Store
faq_agent_arn = get_agent_arn_from_ssm("faq_agent_RuntimeArn")
product_search_agent_arn = get_agent_arn_from_ssm("product_search_agent_RuntimeArn")
inventory_agent_arn = get_agent_arn_from_ssm("inventory_agent_RuntimeArn")
orchestrator_agent_arn = get_agent_arn_from_ssm("orchestrator_agent_boto3_RuntimeArn")

# faq agent test
agent_arn = faq_agent_arn
query = "What is the returns policy of AnyCompany?"

# product agent test
#agent_arn = product_search_agent_arn
#query = "Could you recommend a men's jeans for me?"

# inventory agent test
#agent_arn = inventory_agent_arn
#query = "check availability of PROD-028"

# orchestrator agent test
#agent_arn = orchestrator_agent_arn
#query = "Hello, I am going to attend a party, and would like some suggestions for a midi dress that's available in stock. What can you recommend me?"

print("agent_arn", agent_arn)
print("query", query)
print(invoke_agent_with_boto3(agent_arn, query))