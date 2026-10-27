## Inventory agent prepared for Amazon Bedrock AgentCore runtime deployment.
# To do so we need to make following changes to the Inventory agent created in lab-1b:
#  1. Import the Runtime App with `from bedrock_agentcore.runtime import BedrockAgentCoreApp`
#  2. Initialize the App in our code with `app = BedrockAgentCoreApp()`
#  3. Decorate the invocation function with the `@app.entrypoint` decorator
#  4. Let AgentCoreRuntime control the running of the agent with `app.run()`
##

import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import use_aws


# 1.Import the Runtime App 
from bedrock_agentcore.runtime import BedrockAgentCoreApp
# 2. Initialize the App
app = BedrockAgentCoreApp()


region = boto3.Session().region_name

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
    model=_bedrock_model,
    tools=[get_product],
    system_prompt=_system_prompt
)


# 3. Decorate the invocation function with the `@app.entrypoint` decorator
@app.entrypoint
def invoke_agent(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    response = inventory_agent(user_input)
    return response.message['content'][0]['text']


# 4. Let AgentCoreRuntime control the running of the agent with `app.run()`
if __name__ == "__main__":
    app.run()