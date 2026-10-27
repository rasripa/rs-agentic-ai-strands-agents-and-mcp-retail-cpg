"""Deploy Search Orchestrator Agent to AgentCore Runtime."""

import sys
import time
import json
import os

from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import boto3


region = "us-west-2"
agent_runtime_role = "agent-runtime-role"
# Initialize IAM client
iam = boto3.client('iam', region_name=region)


def create_role_if_not_exists(role_name: str, trust_policy: dict, description: str) -> str:
    """Create IAM role if it doesn't exist, return ARN"""
    try:
        # Check if role exists
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"✅ Role already exists: {role_name}")
        return role_arn
    except iam.exceptions.NoSuchEntityException:
        # Create role
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description
        )
        role_arn = response['Role']['Arn']
        print(f"✅ Created IAM role: {role_name}")
        return role_arn

def attach_policy_if_not_attached(role_name: str, policy_arn: str):
    """Attach managed policy to role if not already attached"""
    try:
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)
        if any(p['PolicyArn'] == policy_arn for p in attached_policies['AttachedPolicies']):
            print(f"  ↳ Policy already attached: {policy_arn.split('/')[-1]}")
        else:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"  ↳ Attached policy: {policy_arn.split('/')[-1]}")
    except Exception as e:
        print(f"  ⚠️  Failed to attach policy: {e}")


def put_inline_policy_if_changed(role_name: str, policy_name: str, policy_document: dict):
    """Put inline policy if it doesn't exist or has changed"""
    try:
        # Check if policy exists
        existing_policy = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        if existing_policy['PolicyDocument'] == policy_document:
            print(f"  ↳ Inline policy unchanged: {policy_name}")
        else:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"  ↳ Updated inline policy: {policy_name}")
    except iam.exceptions.NoSuchEntityException:
        # Create policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"  ↳ Created inline policy: {policy_name}")


def setup_agent_runtime_role():
    """Create IAM role for Agent Runtime"""
    print(" Setting up Agent Runtime Role")

    role_name = agent_runtime_role

    # Trust policy (Bedrock AgentCore can assume this role)
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    # Create role
    role_arn = create_role_if_not_exists(
        role_name,
        trust_policy,
        "Execution role for Agent Runtime"
    )

    # Attach basic execution policy for CloudWatch Logs
    attach_policy_if_not_attached(
        role_name,
        'arn:aws:iam::aws:policy/CloudWatchLogsFullAccess'
    )

    # Inline policy for all agent permissions
    agent_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InvokeMCPServer",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:GetAgentRuntime"
                ],
                "Resource": f"arn:aws:bedrock-agentcore:{region}:*:runtime/*"
            },
            {
                "Sid": "ReadSSMParameters",
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath"
                ],
                "Resource": f"arn:aws:ssm:{region}:*:parameter/*"
            },
            {
                "Sid": "QueryKnowledgeBase",
                "Effect": "Allow",
                "Action": "bedrock:Retrieve",
                "Resource": f"arn:aws:bedrock:{region}:*:knowledge-base/*"
            },
            {
                "Sid": "InvokeBedrockModels",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*::inference-profile/*",
                    f"arn:aws:bedrock:*:*:inference-profile/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "aws-marketplace:ViewSubscriptions",
                    "aws-marketplace:Subscribe",
                    "aws-marketplace:Unsubscribe"
                ],
                "Resource": "*"
            },
            {
                "Sid": "InvokeAgentCoreGateway",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetGateway",
                    "bedrock-agentcore:InvokeGateway"
                ],
                "Resource": f"arn:aws:bedrock-agentcore:{region}:*:gateway/*"
            },
            {
                "Sid": "ReadDynamoDB",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable"
                ],
                "Resource": f"arn:aws:dynamodb:{region}:*:table/*"
            },
            {
                "Sid": "XRayTracing",
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets"
                ],
                "Resource": "*"
            }
        ]
    }

    put_inline_policy_if_changed(role_name, "AgentPermissions", agent_policy)

    # Inline policy for ECR access (required by AgentCore Runtime to pull Docker images)
    ecr_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": "*"
        }]
    }

    put_inline_policy_if_changed(role_name, "ECRAccess", ecr_policy)

    return role_arn


def deploy_agent(agent_name, agent_file_name):
    """Deploy the Agent to AgentCore Runtime."""

    print(f"Deploying {agent_name} to AgentCore Runtime")
    print(f"Using AWS region: {region}")

    # Get AWS account ID and construct IAM role ARN
    sts_client = boto3.client('sts', region_name=region)
    account_id = sts_client.get_caller_identity()['Account']
    execution_role_arn = agent_runtime_role
    agent_name = agent_name

    print(f"Using execution role: {execution_role_arn}")

    # Initialize AgentCore Runtime
    agentcore_runtime = Runtime()

    # Configure the runtime
    print("Configuring AgentCore Runtime...")
    try:
        # Use pre-created IAM role with all necessary permissions
        # Configure AgentCore Runtime with entrypoint agent, protocol, execution role, name
        response = agentcore_runtime.configure(
            entrypoint=agent_file_name,
            auto_create_execution_role=False,
            execution_role=execution_role_arn,
            auto_create_ecr=True,
            requirements_file="requirements.txt",
            region=region,
            agent_name=agent_name
        )
        print("Configuration completed")
    except Exception as e:
        print(f"Configuration failed: {e}")
        sys.exit(1)

    # Launch the runtime
    print("Launching Agent (this takes 5-8 minutes)...")

    try:
        launch_result = agentcore_runtime.launch()
        print(f"Launch initiated")
        print(f"Agent ARN: {launch_result.agent_arn}")
        print(f"Agent ID: {launch_result.agent_id}")
    except Exception as e:
        print(f"Launch failed: {e}")
        sys.exit(1)

    # Wait for deployment to complete
    print("Waiting for deployment to complete...")

    max_wait_time = 600  # 10 minutes
    start_time = time.time()

    while True:
        try:
            status_response = agentcore_runtime.status()
            status = status_response.endpoint['status']
            if status == 'READY':
                print("Agent is READY!")
                break
            elif status in ['CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']:
                print(f"Deployment failed with status: {status}")
                sys.exit(1)
            else:
                print(f"   Status: {status}...")

        except Exception as e:
            print(f"   Checking status...")

        if time.time() - start_time > max_wait_time:
            print("Timeout waiting for deployment")
            sys.exit(1)

        time.sleep(10)

    # Store deployment info for agent to use
    print("Storing deployment information...")
    # Store in Parameter Store for easy retrieval
    ssm_client = boto3.client('ssm', region_name=region)
    ssm_param_name = f"{agent_name}_RuntimeArn"
    try:
        
        ssm_client.put_parameter(
            Name=ssm_param_name,
            Value=launch_result.agent_arn,
            Type='String',
            Description='Search Orchestrator Agent ARN',
            Overwrite=True
        )
        print("✅ AgentRuntimeArn stored in SSM Parameter store", ssm_param_name)
    except Exception as e:
        print(f"Warning: Could not store in Parameter Store: {e}")

    # Print summary
    print("\n" + "="*60)
    print("Agent Deployment Successful!!")
    print("="*60)
    print(f"Agent Name: {agent_name}")
    print(f"Agent ARN: {launch_result.agent_arn}")
    print(f"Agent ARN SSM Parameter Key: {ssm_param_name}")

    # Rename Dockerfile and .bedrock_agentcore.yaml with agent_name suffix
    # so they don't get overwritten by the next agent deployment
    for filename in ["Dockerfile", ".bedrock_agentcore.yaml"]:
        if os.path.exists(filename):
            new_name = f"{filename}_{agent_name}"
            os.rename(filename, new_name)
            print(f"  ↳ Renamed {filename} → {new_name}")
    
    return launch_result


if __name__ == "__main__":
    agent_runtime_role = setup_agent_runtime_role()
    print ("agent_runtime_role :: ", agent_runtime_role)

    # faq agent
    deploy_agent("faq_agent", "faq-agent-agentcore.py")

    # inventory agent
    deploy_agent("inventory_agent", "inventory-agent-agentcore.py")

    # product search agent
    deploy_agent("product_search_agent", "product-search-agent-agentcore.py")

    # orchestrator agent using boto3 to invoke sub agents
    deploy_agent("orchestrator_agent_boto3", "orchestrator-agent-boto3-agentcore.py")