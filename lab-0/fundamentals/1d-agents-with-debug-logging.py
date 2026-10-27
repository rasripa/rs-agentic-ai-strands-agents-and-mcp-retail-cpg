import boto3
from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
import logging

region = boto3.Session().region_name

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.DEBUG)

# Sets the logging format and streams logs. prints the detailed trace steps and event loop cycles
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Create a boto client config with custom settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30
)

# Create a Bedrock model instance
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", # try with different models you enabled access
    region_name=region,
    temperature=0.3,
    boto_client_config=boto_config,
)

# Create an agent using the BedrockModel instance
agent = Agent(model=bedrock_model)

# Use the agent
agent_response_with_nova_premier = agent("Tell me about Amazon Bedrock.")