## FAQ agent prepared with A2A
import os
import boto3
from strands import Agent, tool
from strands_tools import retrieve
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
import sys

from strands.multiagent.a2a import A2AServer
from fastapi import FastAPI
import uvicorn


region = boto3.Session().region_name

runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')
host, port = "0.0.0.0", 9000


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

# Get Agent Model ID from SSM Parameter Store
agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
print(f"Agent Model ID is {agent_model_id}")

# Create a boto client config with custom settings
_boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60
)

# Create a Bedrock model instance
_bedrock_model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3,
    boto_client_config=_boto_config,
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


faq_agent = Agent(
    name="FAQ Agent",
    description="Answers questions about AnyCompany's profile, retail policies, financial performance, annual reports, terms and conditions.",
    tools=[get_anycompany_docs],
    model=_bedrock_model,
    system_prompt="You are a friendly agent that answers questions about AnyCompany's profile, retail policies, financial performance, annual reports, terms and conditions etc.",
)



a2a_server = A2AServer(
    agent=faq_agent,
    http_url=runtime_url,
    serve_at_root=True
)

# Log the auto-generated agent card so we can see what gets served at /.well-known/agent-card.json
import json as _json
print("📋 FAQ Agent Card (served at /.well-known/agent-card.json):")
print(_json.dumps(a2a_server.public_agent_card.model_dump(mode="json", exclude_none=True), indent=2))

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "healthy"}


app.mount("/", a2a_server.to_fastapi_app())

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)