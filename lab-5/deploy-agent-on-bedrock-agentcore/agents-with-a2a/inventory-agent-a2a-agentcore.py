## Inventory agent prepared with A2A

import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import use_aws


from strands.multiagent.a2a import A2AServer
from fastapi import FastAPI
import uvicorn


region = boto3.Session().region_name

runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')
host, port = "0.0.0.0", 9000

# Get Agent Model ID from SSM Parameter Store
ssm_client = boto3.client('ssm', region_name=region)
agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
print(f"Agent Model ID is {agent_model_id}")

# Create a Bedrock model instance
_bedrock_model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3
)


_aws_agent = Agent(tools=[use_aws])

@tool
def get_product(product_id: str):
    """
    Use this tool when you need to get the details of a product to 
    see if that's available in stock or not.

    Args:
        product_id: The id of the product

    """
    print(f"Getting product from Dynamodb with the input {product_id}")

    get_item_result = _aws_agent.tool.use_aws(
        service_name="dynamodb",
        operation_name="get_item",
        parameters={
            "TableName": "anycompany_product_inventory",
            "Key":{
                "product_id": {
                    "S": product_id
            }
            }
            },
        region=region,
        label="Get One Item"
    )
    return get_item_result


_system_prompt = """
You are an Agent that checks if a product is available in the inventory.
Return output in the below JSON format. Do not include any other text.
{
    "product_id" : PRODUCT_ID,
    "in_stock": IN_STOCK_VALUE
}

where IN_STOCK_VALUE = "yes" if quantity_available is > 0 and "no" otherwise.
"""

# Register the tool with the agent
inventory_agent = Agent(
    name="Inventory Agent",
    description="Checks if a product is available in the inventory by looking up stock levels in DynamoDB.",
    model=_bedrock_model,
    tools=[get_product],
    system_prompt=_system_prompt
)


a2a_server = A2AServer(
    agent=inventory_agent,
    http_url=runtime_url,
    serve_at_root=True
)

# Log the auto-generated agent card so we can see what gets served at /.well-known/agent-card.json
import json as _json
print("📋 Inventory Agent Card (served at /.well-known/agent-card.json):")
print(_json.dumps(a2a_server.public_agent_card.model_dump(mode="json", exclude_none=True), indent=2))

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "healthy"}


app.mount("/", a2a_server.to_fastapi_app())

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)