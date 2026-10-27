import os
import sys
import boto3
from strands import Agent
from strands_tools import retrieve
from strands.tools import tool
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError

region = boto3.Session().region_name

##################################
# Get FAQ Knowledge Base ID from SSM Parameter Store
try:
    ssm_client = boto3.client('ssm', region_name=region)
    response = ssm_client.get_parameter(Name="faq_kb_id")
    kb_id = response['Parameter']['Value']
    print(f"Successfully retrieved FAQ Knowledge Base ID: {kb_id}")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'ParameterNotFound':
        print("ERROR: SSM parameter 'faq_kb_id' does not exist.")
        print("Please create the SSM parameter 'faq_kb_id' with your FAQ Knowledge Base ID before running this script.")
        sys.exit(1)
    else:
        print(f"ERROR: Failed to retrieve SSM parameter 'faq_kb_id': {str(e)}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error retrieving SSM parameter 'faq_kb_id': {str(e)}")
    sys.exit(1)
##################################

##################################
# Get Agent Model ID from SSM Parameter Store
try:
    response = ssm_client.get_parameter(Name="agent_model_id")
    agent_model_id = response['Parameter']['Value']
    print(f"Successfully retrieved Agent Model ID: {agent_model_id}")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'ParameterNotFound':
        print("ERROR: SSM parameter 'agent_model_id' does not exist.")
        print("Please create the SSM parameter 'agent_model_id' with your model ID before running this script.")
        sys.exit(1)
    else:
        print(f"ERROR: Failed to retrieve SSM parameter 'agent_model_id': {str(e)}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error retrieving SSM parameter 'agent_model_id': {str(e)}")
    sys.exit(1)
##################################

# Create a boto client config with custom settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60
)

# Create a Bedrock model instance
bedrock_model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3,
    boto_client_config=boto_config,
)

@tool
def get_anycompany_docs(user_query: str) -> str:
    try:        
        # Use strands retrieve tool
        tool_use = {
            "toolUseId": "get_anycompany_docs",
            "input": {
                "text": user_query,
                "knowledgeBaseId": kb_id,
                "region": region,
                "numberOfResults": 3,
                "score": 0.4
            }
        }
        result = retrieve.retrieve(tool_use)

        if result["status"] == "success":
            return result["content"][0]["text"]
        else:
            return f"Unable to access technical support documentation. Error: {result['content'][0]['text']}"

    except Exception as e:
        print(f"Detailed error in get_anycompany_docs: {str(e)}")
        return f"Unable to access anycompany documentation. Error: {str(e)}"


# Create the Agent. Pass the "retrieve" tool in the tools list.
faq_agent = Agent(
    tools=[get_anycompany_docs],
    model=bedrock_model,
    system_prompt="You are a friendly agent that answers questions about AnyCompany's profile, retail policies, financial performance, annual reports, terms and conditions etc.",
)

result1 = faq_agent("What is the returns policy of AnyCompany?")
print(result1)

result2 = faq_agent("When was AnyCompany established?")
print(result2)

result3 = faq_agent("What is your contact center phone number?")
print(result3)