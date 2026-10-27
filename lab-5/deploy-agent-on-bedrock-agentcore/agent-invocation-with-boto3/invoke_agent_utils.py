"""
Utility to invoke sub-agents on AgentCore Runtime via boto3.

Reference: awslabs/amazon-bedrock-agentcore-samples
  01-tutorials/01-AgentCore-runtime/03-advanced-concepts/05-multi-agents/
  01-multi-runtimes-with-boto3/orchestrator_agent/invoke_agent_utils.py
"""

import boto3
import json
import logging

logger = logging.getLogger(__name__)


def invoke_agent_with_boto3(agent_arn: str, user_query: str) -> str:
    """
    Invoke a sub-agent deployed on AgentCore Runtime using boto3.

    Args:
        agent_arn: The ARN of the AgentCore Runtime to invoke.
        user_query: The user's query to send to the sub-agent.

    Returns:
        The agent's response as a string.
    """
    agentcore_client = boto3.client('bedrock-agentcore')

    logger.info(f"Invoking agent: {agent_arn}")
    boto3_response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": user_query})
    )

    if "text/event-stream" in boto3_response.get("contentType", ""):
        # Handle streaming response
        result = ""
        for line in boto3_response["response"].iter_lines(chunk_size=1):
            if line:
                line = line.decode("utf-8")
                line = line[6:]  # Strip "data: " prefix
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                line = line.replace('\\n', '\n')
                result += line
    else:
        # Handle non-streaming response
        response_body = boto3_response['response'].read()
        response_data = json.loads(response_body)
        result = response_data

    return result
