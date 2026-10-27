## Product Search agent prepared for A2A

import boto3
import os
from strands import Agent, tool
from strands_tools import retrieve
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client


from strands.multiagent.a2a import A2AServer
from fastapi import FastAPI
import uvicorn


app = FastAPI()
runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')
host, port = "0.0.0.0", 9000


# Configure region, SSM client and AgentCore Gateway

# Set up AWS region and get configuration from SSM Parameter Store
region = boto3.Session().region_name
print(f"Using AWS region: {region}")

# Initialize SSM client
ssm_client = boto3.client('ssm', region_name=region)

# Retrieve configuration parameters - AgentCore Gateway has been previously created
try:
    prod_search_kb_id = ssm_client.get_parameter(Name="product_search_kb_id")['Parameter']['Value']
    prod_search_agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
    agentcore_mcp_gatewayURL = ssm_client.get_parameter(Name="anycomp_prod_reviews_mcp_server_url")['Parameter']['Value']
    anycomp_agcore_gw_cognito_accesstoken = ssm_client.get_parameter(Name="anycomp_agcore_gw_cognito_accesstoken")['Parameter']['Value']

    print("✅ Configuration parameters retrieved successfully!")
    print(f"Knowledge Base ID: {prod_search_kb_id}")
    print(f"Model ID: {prod_search_agent_model_id}")
    print(f"MCP Gateway URL: {agentcore_mcp_gatewayURL}")
    
except Exception as e:
    print(f"❌ Error retrieving parameters: {e}")
    print("Please ensure all required SSM parameters are configured.")
    raise

# Validate AgentCore Gateway configuration
if agentcore_mcp_gatewayURL == "NOT CONFIGURED":
    raise ValueError(
        "❌ AgentCore Gateway is not configured! Please configure the AgentCore Gateway by following Lab 2 instructions"
    )

# Create a Bedrock model instance
_bedrock_model = BedrockModel(
    model_id=prod_search_agent_model_id,
    region_name=region,
    temperature=0.3
)

print(f"✅ Bedrock model initialized: {prod_search_agent_model_id}")

# Define the tool to fetch data from the product knowledge base
@tool
def get_products_from_kb(user_query: str) -> str:
    """
    Use this tool when you need to search for products 
    in the Knowledge Base that match user's product search query.

    Args:
        user_query: The user's product search query

    """    
    try:        
        # Use strands retrieve tool
        tool_use = {
            "toolUseId": "get_products_from_kb",
            "input": {
                "text": user_query,
                "knowledgeBaseId": prod_search_kb_id,
                "region": region,
                "numberOfResults": 5,
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


# Define the system prompt for the AI shopping assistant
system_prompt = """
You are an AI shopping assistant that helps customers discover products and reviews. 
You have access to:
1. A tool for searching for products that match with user's product search query
2. A MCP tool for retrieving detailed product reviews and ratings

When a customer asks about products:
1. First, search the knowledge base for relevant products using the search_products tool
2. If available and relevant, retrieve reviews for the products using MCP tools
3. Provide helpful recommendations based on the information gathered
4. Always format responses in a clear, customer-friendly manner
5. Include relevant product details like price, features, and availability when available

Guidelines:
- Be helpful, accurate, and informative
- Provide structured responses when possible
- If you cannot find specific information, clearly state this
- Always prioritize customer needs and preferences
- Suggest alternatives when the exact request cannot be fulfilled
- Include review summaries and ratings when available

Response Format:
- Start with a brief summary of findings
- List recommended products with key in the below JSON array format -
[
   { "product_id": "PROD-010", 
     "product_name": "Uniqlo Ultra Light Down Jacket", 
     "brand_name": "Uniqlo", 
     "category": "Clothing", 
     "subcategory": "Outerwear", 
     "gender": "Unisex", 
     "price": 69.90, 
     "sale_price": 49.90, 
     "size": ["XS", "S", "M", "L", "XL", "XXL"], 
     "color": ["Black", "Navy", "Red", "Olive", "Grey"], 
     "materials": ["100% Nylon", "Down filling", "Water-repellent coating"], 
     "season": "Fall/Winter",
     "product_review": "review summary of the current product"
     },
     ...
]

"""


# Define the main function that handles product search queries using the Knowledge Base and MCP tools.
# Create the product search agent with the KB tool.
# MCP tools will be added on startup when the MCP client connects.
product_search_agent = Agent(
    name="Product Search Agent",
    description="Discovers products for customers based on their requirements using a knowledge base and product reviews via MCP.",
    tools=[get_products_from_kb],
    model=_bedrock_model,
    system_prompt=system_prompt
)

# Global MCP client with lazy initialization
_mcp_client = None

async def get_mcp_client():
    """Lazy initialization of MCP client"""
    global _mcp_client
    if _mcp_client is None:
        try:
            _mcp_client = MCPClient(lambda: streamablehttp_client(
                agentcore_mcp_gatewayURL,
                headers={"Authorization": f"Bearer {anycomp_agcore_gw_cognito_accesstoken}"}
            ))
            _mcp_client.__enter__()
            print("✅ MCP client initialized")
        except Exception as e:
            print(f"❌ MCP client failed: {e}")
            _mcp_client = None
    return _mcp_client

async def setup_agent_tools():
    """Setup agent tools when MCP client is ready"""
    try:
        mcp_client = await get_mcp_client()
        if mcp_client:
            mcp_tools = mcp_client.list_tools_sync()
            product_search_agent.tools.append(mcp_tools)
            print("✅ MCP tools registered with product search agent")
    except Exception as e:
        print(f"⚠️ Could not setup MCP tools: {e}")


a2a_server = A2AServer(
    agent=product_search_agent,
    http_url=runtime_url,
    serve_at_root=True
)

# Log the auto-generated agent card so we can see what gets served at /.well-known/agent-card.json
import json as _json
print("📋 Product Search Agent Card (served at /.well-known/agent-card.json):")
print(_json.dumps(a2a_server.public_agent_card.model_dump(mode="json", exclude_none=True), indent=2))

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup and register MCP tools with the agent."""
    await setup_agent_tools()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP client on shutdown."""
    if _mcp_client:
        _mcp_client.__exit__(None, None, None)

app.mount("/", a2a_server.to_fastapi_app())

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)