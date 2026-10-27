import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# Import the FAQAgent from the local python in lab 4. This has the code that we saw in the FAQ Agents lab.
from FAQAgent import faq_agent

# Import Product Search and Inventory Agents from local python files.
from ProductSearchAgent import product_search_agent
from InventoryAgent import inventory_agent

region = boto3.Session().region_name
print(f"Using AWS region: {region}")

# Initialize SSM client
ssm_client = boto3.client('ssm', region_name=region)

# Get Agent Model ID from SSM Parameter Store
agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
print(f"Agent Model ID is {agent_model_id}")

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
def faq_agent_tool(query: str) -> str:
    """
    Answers questions about AnyCompany.
    
    Use this tool when you need to find answers to general questions about the
    policies, procedures, or common inquiries of AnyCompany.

    Args:
        query: The search question. (String)
    
    Returns:
        The answer to the question (String)

    """
    print("Fetching from FAQ Knowledge Base")
    response = faq_agent(query)
    print(f"The response from FAQ Agent is {response}")
    return response


@tool
def product_search_agent_tool(query: str) -> str:
    """ 
    Discovers products for customers based on their requirements.

    Use this tool when you need to discover some products based
    on the requirements of the customer.

    Args:
        query: The search requirements from the customer

    Returns:
        A list of matching product records, each containing:
        - id: Unique product identifier (string)
        - product_name: Product name
        - brand_name: Brand name
        - category: Category of the product
        - subcategory: Sub category
        - gender: Gender that the product applies to
        - price: Price
        - sale_price: Sales price
        - size: Available sizes as an array
        - color: Available colors as an array
        - materials: Materials
        - season: Season
        - product_review: Review summary of the product.
       
       Example response:
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
    print("Fetching from Product Search Knowledge Base using the query " + query)

    kbRes = product_search_agent(query)

    print(f"Products fetched from KB are : {kbRes}")
    return kbRes


@tool
def inventory_agent_tool(query: str) -> str:
    """ 
    Checks the inventory of products.

    Use this tool if you want to check if a product is in stock or not.

    This tool uses the Inventory Agent to find out if the product
    is in stock or not.

    Args:
        query: The product Id (String)
    
    Returns:
        A JSON containing the fields:
        - product_id: Unique product identifier (String)
        - in_stock: "yes" or "no" indicating if the product is in stock or not.

        Example response:
        {
            "product_id" : PRODUCT_ID,
            "in_stock": IN_STOCK_VALUE
        }

    """
    print("Fetching from Inventory Agent with the query " + query)
    result = inventory_agent(query)
    print(f"Result from inventory_agent_tool is \" {result} \"")
    print("----------------------------")
    return result

# Search Orchestrator
ORCHESTRATOR_SYSTEM_PROMPT = """You are the Search Orchestrator Agent, a sophisticated AI coordinator 
responsible for managing and directing queries to three specialized collaborator agents: the FAQ Agent, 
the Product Search Agent, and the Inventory Agent. Your primary role is to efficiently handle user 
inquiries by determining which agent(s) to engage and in what order.

Your key responsibilities include:
1. Analyze incoming user queries to understand their intent and requirements.
2. Decide which tool(s) to consult based on the nature of the query:
   - FAQ Agent Tool: For general questions about policies, procedures, or common inquiries. This tool does 
                     not have product or product availability related information.
   - Product Search Agent Tool: For queries related to finding specific products or product categories.
   - Inventory Agent Tool: For questions about stock levels and availability.
3. Determine the optimal sequence for consulting these tools if multiple tools are needed.
4. Formulate clear, concise sub-queries for each relevant tool.
5. Collect and synthesize responses from the collaborator tools.
6. Generate a comprehensive, coherent response for the user based on the information gathered.

Note:
1. Fetch product availability information only when explicitly asked by the customer. 
2. FAQ Agent Tool does not have product or product availability related information.

Remember, your goal is to provide accurate, helpful, and efficient responses to user queries by 
leveraging the specialized knowledge of each collaborator tool. Always strive for clarity, 
conciseness, and relevance in your communications with both users and collaborator tools.
"""

# Create the orchestrator agent with the collaborator Agents as tools.
orchestrator = Agent(
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[faq_agent_tool, product_search_agent_tool, inventory_agent_tool],
    model=bedrock_model
)

print("################Test 1#####################")
result1 = orchestrator("What is the returns policy of AnyCompany?")
print(result1)
print("----------------------------------------")

print("################Test 2#####################")
result2 = orchestrator("Could you recommend a men's jeans for me?")
print(result2)
print("----------------------------------------")

print("################Test 3#####################")
result3 = orchestrator("Hello, I am going to attend a party and would like some suggestions for a midi dress that's available in stock. Show product reviews as well. What can you recommend me?")
print(result3)
print("----------------------------------------")