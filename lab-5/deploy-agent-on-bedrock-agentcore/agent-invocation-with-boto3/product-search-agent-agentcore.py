## Product Search agent prepared for Amazon Bedrock AgentCore runtime deployment.
# To do so we need to make following changes to the Product Search agent created in lab-1b:
#  1. Import the Runtime App with `from bedrock_agentcore.runtime import BedrockAgentCoreApp`
#  2. Initialize the App in our code with `app = BedrockAgentCoreApp()`
#  3. Decorate the invocation function with the `@app.entrypoint` decorator
#  4. Let AgentCoreRuntime control the running of the agent with `app.run()`
##

import boto3
import os
from strands import Agent, tool
from strands_tools import retrieve
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client


# 1.Import the Runtime App 
from bedrock_agentcore.runtime import BedrockAgentCoreApp
# 2. Initialize the App
app = BedrockAgentCoreApp()


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
def invoke_product_search_agent(input_query):
    """
    Main function to retrieve product details based on user query.
    
    Args:
        input_query (str): User's product search query
        
    Returns:
        str: Product search results in JSON format
    """
    print(f"Processing query: {input_query}")
    
    # MCPClient that connects to the MCPServer hosted in AgentCore Gateway which has a tool that returns product reviews.
    streamable_http_mcp_client = MCPClient(lambda:streamablehttp_client(agentcore_mcp_gatewayURL,headers={"Authorization": f"Bearer {anycomp_agcore_gw_cognito_accesstoken}"}))
    
    product_search_results = ''

    try:
        with streamable_http_mcp_client:
            # Get the tools from the MCP Server.
            mcp_tools_in_agentcore_gateway = streamable_http_mcp_client.list_tools_sync()

            product_search_agent = Agent(
                tools=[get_products_from_kb, mcp_tools_in_agentcore_gateway],
                model=_bedrock_model,
                system_prompt=system_prompt
            )
            product_search_results = str(product_search_agent(input_query))
        
    except Exception as e:
        print(f"❌ Error during product search: {e}")
        return f"Error: {str(e)}"
    
    return product_search_results



# 3. Decorate the invocation function with the `@app.entrypoint` decorator
@app.entrypoint
def invoke_agent (payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    response = invoke_product_search_agent(user_input)
    return response


# 4. Let AgentCoreRuntime control the running of the agent with `app.run()`
if __name__ == "__main__":
    app.run()