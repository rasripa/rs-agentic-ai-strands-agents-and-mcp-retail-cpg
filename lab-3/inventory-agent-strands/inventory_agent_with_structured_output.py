"""
    Use this file to test structured output with Claude Haiku. 
    This example uses a Pydantic model to constrain Claude's output. 
    Run with: python inventory_agent_with_structured_output_for_Claude.py

    The orchestrator agent in this multi-agentic architecture does not require structure response, 
    and only needs inventory availability status. Hence, we will be using the code 
    from the previous example (without structured output) to create the agent in the following labs.

"""

# import all libraries
import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import use_aws
from pydantic import BaseModel, Field
from typing import Literal

region = boto3.Session().region_name

# Get Agent Model ID from SSM Parameter Store
ssm_client = boto3.client('ssm', region_name=region)
agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
print(f"Agent Model ID is {agent_model_id}")

model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3,
)

aws_agent = Agent(tools=[use_aws])

@tool
def get_product(product_id: str):
    """
    Look up a product in DynamoDB to check whether it is in stock.

    Args:
        product_id: The id of the product (e.g. PROD-048).
    """
    print(f"Getting product from Dynamodb with the input {product_id}")

    return aws_agent.tool.use_aws(
        service_name="dynamodb",
        operation_name="get_item",
        parameters={
            "TableName": "anycompany_product_inventory",
            "Key": {"product_id": {"S": product_id}},
        },
        region=region,
        label="Get One Item",
    )

# Pydantic schema — Claude Haiku is constrained to emit JSON matching this shape.
class InventoryStatus(BaseModel):
    """Inventory availability for a single product."""
    product_id: str = Field(description="The product id from the user query, e.g. PROD-048")
    in_stock: Literal["yes", "no"] = Field(
        description="'yes' when quantity_available > 0, otherwise 'no'"
    )

# Claude-friendly prompt: imperative steps, clear decision rule, no formatting noise.
_system_prompt = """You are an inventory-checking agent.

For every user request:
1. Call the `get_product` tool with the product_id mentioned in the query.
2. Read the `quantity_available` attribute from the tool response.
3. Decide in_stock: 'yes' when quantity_available > 0, otherwise 'no'.

Return only the structured result. Do not add commentary or formatting.
"""

inventory_agent = Agent(
    model=model,
    tools=[get_product],
    system_prompt=_system_prompt,
)

# --- Test 1: PROD-048 ---
product_agent_response = inventory_agent(
    "What is the available quantity for PROD-048?",
    structured_output_model=InventoryStatus,
)
prod_048: InventoryStatus = product_agent_response.structured_output
print("\nPROD-048 — raw JSON result:")
print(prod_048.model_dump_json(indent=2))

# --- Test 2: PROD-028 ---
quantity_agent_response = inventory_agent(
    "How many PROD-028 are available?",
    structured_output_model=InventoryStatus,
)
prod_028: InventoryStatus = quantity_agent_response.structured_output
print("\nPROD-028 — raw JSON result:")
print(prod_028.model_dump_json(indent=2))