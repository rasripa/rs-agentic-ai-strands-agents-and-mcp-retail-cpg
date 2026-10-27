## Orchestrator agent that invokes sub-agents via boto3 on AgentCore Runtime.
#
# This orchestrator is deployed as an HTTP agent (BedrockAgentCoreApp) and calls
# three sub-agents (FAQ, Product Search, Inventory) using boto3 invoke_agent_runtime.
#
# Pattern reference: awslabs/amazon-bedrock-agentcore-samples
#   01-tutorials/01-AgentCore-runtime/03-advanced-concepts/05-multi-agents/
#   01-multi-runtimes-with-boto3/orchestrator_agent/orchestrator_agent.py
##

import logging
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from invoke_agent_utils import invoke_agent_with_boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

region = boto3.Session().region_name
logger.info(f"Using AWS region: {region}")

# --- Retrieve sub-agent ARNs from SSM ---

ssm_client = boto3.client('ssm', region_name=region)

# Get Agent Model ID from SSM Parameter Store
agent_model_id = ssm_client.get_parameter(Name="agent_model_id")['Parameter']['Value']
logger.info(f"Agent Model ID is {agent_model_id}")

def get_agent_arn(agent_name: str) -> str:
    """Retrieve agent ARN from SSM Parameter Store."""
    try:
        response = ssm_client.get_parameter(Name=f'{agent_name}_RuntimeArn')
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get ARN for {agent_name}: {e}")
        raise


# --- Bedrock model for the orchestrator ---

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60
)

bedrock_model = BedrockModel(
    model_id=agent_model_id,
    region_name=region,
    temperature=0.3,
    boto_client_config=boto_config,
)


# --- Tools that invoke sub-agents via boto3 ---

@tool
def faq_agent_tool(query: str) -> str:
    """
    Answers questions about AnyCompany.

    Use this tool when you need to find answers to general questions about the
    policies, procedures, or common inquiries of AnyCompany.

    Args:
        query: The search question.

    Returns:
        The answer to the question.
    """
    logger.info(f"Calling FAQ agent via boto3: {query[:100]}")
    try:
        faq_agent_arn = get_agent_arn("faq_agent")
        return invoke_agent_with_boto3(faq_agent_arn, user_query=query)
    except Exception as e:
        logger.exception("Exception calling FAQ agent")
        return str(e)


@tool
def product_search_agent_tool(query: str) -> str:
    """
    Discovers products for customers based on their requirements.

    Use this tool when you need to discover products based on customer requirements.

    Args:
        query: The search requirements from the customer.

    Returns:
        A list of matching product records in JSON format.
    """
    logger.info(f"Calling Product Search agent via boto3: {query[:100]}")
    try:
        product_search_agent_arn = get_agent_arn("product_search_agent")
        return invoke_agent_with_boto3(product_search_agent_arn, user_query=query)
    except Exception as e:
        logger.exception("Exception calling Product Search agent")
        return str(e)


@tool
def inventory_agent_tool(query: str) -> str:
    """
    Checks the inventory of products.

    Use this tool if you want to check if a product is in stock or not.

    Args:
        query: The product Id.

    Returns:
        A JSON with product_id and in_stock status.
    """
    logger.info(f"Calling Inventory agent via boto3: {query[:100]}")
    try:
        inventory_agent_arn = get_agent_arn("inventory_agent")
        return invoke_agent_with_boto3(inventory_agent_arn, user_query=query)
    except Exception as e:
        logger.exception("Exception calling Inventory agent")
        return str(e)


# --- Orchestrator Agent ---

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

orchestrator = Agent(
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[faq_agent_tool, product_search_agent_tool, inventory_agent_tool],
    model=bedrock_model
)


# --- Entrypoint ---

@app.entrypoint
def strands_agent_bedrock(payload):
    """
    Invoke the orchestrator agent with a payload.
    The orchestrator calls sub-agents via boto3 invoke_agent_runtime on AgentCore Runtime.
    """
    ## Sample input prompts for testing
    # 1. What is the returns policy of AnyCompany?
    # 2. Could you recommend a men's jeans for me?
    # 3. Hello, I am going to attend a party and would like some suggestions for a midi dress
    #    that's available in stock. Show product reviews as well. What can you recommend me?
    ##
    user_input = payload.get("prompt")
    logger.info(f"User input: {user_input}")
    response = orchestrator(user_input)
    return response.message['content'][0]['text']


if __name__ == "__main__":
    app.run()
