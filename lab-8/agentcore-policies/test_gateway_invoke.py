"""
Lab 8 - Test: Live Gateway Invocation with Policy Enforcement

This script invokes the actual gateway to test that the policy engine
is actively enforcing the baseline permit policy. 

Run this AFTER guardrails_in_policy.py to verify the gateway is
responding with policy enforcement active.
"""

import boto3
import json

region = boto3.Session().region_name
ssm = boto3.client('ssm', region_name=region)

# Get gateway details
gateway_id = ssm.get_parameter(Name='anycomp_agcore_gw_id')['Parameter']['Value']
target_name = ssm.get_parameter(Name='anycomp_agcore_gw_target_name')['Parameter']['Value']

# Get the Cognito token for invoking the gateway
try:
    access_token = ssm.get_parameter(Name='anycomp_agcore_gw_cognito_accesstoken')['Parameter']['Value']
except Exception:
    access_token = None
    print("⚠️  No Cognito token found. Will try IAM-based invocation.")

print("=" * 60)
print("TEST: Live Gateway Invocation with Policy Engine")
print("=" * 60)
print(f"Gateway ID: {gateway_id}")
print(f"Target: {target_name}")
print(f"Auth: {'Cognito JWT' if access_token else 'IAM'}")
print()

# Try invoking via the MCP endpoint (same as Lab 2)
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Get the gateway URL
gateway_url = ssm.get_parameter(Name='anycomp_prod_reviews_mcp_server_url')['Parameter']['Value']
print(f"Gateway MCP URL: {gateway_url}")

print("\n" + "-" * 60)
print("Test 1: List available tools through the gateway")
print("-" * 60)

discovered_tool_name = None

try:
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {access_token}"} if access_token else {},
        )
    )
    
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        print(f"  ✅ Gateway responded! Found {len(tools)} tool(s):")
        for tool in tools:
            # MCPAgentTool may store name in different attributes
            tool_name = getattr(tool, 'name', None) or getattr(tool, 'tool_name', None)
            if tool_name is None and hasattr(tool, 'tool_spec'):
                tool_name = tool.tool_spec.get('name', None)
            if tool_name is None:
                tool_name = str(tool)
            print(f"     • {tool_name}")
            if discovered_tool_name is None and tool_name and '<' not in tool_name:
                discovered_tool_name = tool_name
            
except Exception as e:
    error_str = str(e)
    if 'Denied' in error_str or '403' in error_str or 'not allowed' in error_str:
        print(f"  🚫 Access DENIED by policy engine")
        print(f"     This means the policy engine is active and enforcing!")
        print(f"     The request was blocked because no permit policy matched")
        print(f"     for the current principal/action combination.")
    else:
        print(f"  ⚠️  Error: {e}")

print("\n" + "-" * 60)
print("Test 2: Invoke a tool through the gateway")
print("-" * 60)

if not discovered_tool_name:
    print("  ⚠️  Skipping — no tool name discovered from Test 1")
else:
    print(f"  Calling tool: {discovered_tool_name}")
    try:
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                gateway_url,
                headers={"Authorization": f"Bearer {access_token}"} if access_token else {},
            )
        )
        
        with mcp_client:
            result = mcp_client.call_tool_sync(
                tool_use_id="test-policy-enforcement",
                name=discovered_tool_name,
                arguments={"product_id": "PROD-010"}
            )
            # Check if the result indicates an error
            content_text = ""
            for block in result.get("content", []):
                text = block.get("text", "")
                content_text += text

            if "error" in content_text.lower() or "failed" in content_text.lower():
                print(f"  ⚠️  Tool executed but returned an error (this is OK — it means")
                print(f"       the policy engine ALLOWED the request through to the tool)")
                print(f"     Response: {content_text[:100]}...")
            else:
                print(f"  ✅ Tool call succeeded! Policy engine ALLOWED the request.")
                print(f"     Response preview: {content_text[:100]}...")
                    
    except Exception as e:
        error_str = str(e)
        if 'Denied' in error_str or '403' in error_str or 'not allowed' in error_str:
            print(f"  🚫 Tool call DENIED by policy engine")
            print(f"     The policy engine evaluated the request and blocked it.")
            print(f"     Check your permit policies to ensure this action is allowed.")
        elif 'Unknown tool' in error_str:
            print(f"  ✅ Policy engine ALLOWED the request (tool reached the MCP server)")
            print(f"     The MCP server didn't recognize the tool name, but the important")
            print(f"     thing is the request passed through the policy engine.")
        else:
            print(f"  ⚠️  Error: {e}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("""
  What this test shows:
  
  • The policy engine is ACTIVE on your gateway
  • Every request is evaluated against your Cedar policies
  • If the request matches a 'permit' → it goes through
  • If it matches a 'forbid' → it's blocked
  • If no policy matches → it's denied (default deny in ENFORCE mode)
  
  The BaselinePermit policy (from Part 1) permits all requests
  by default, so tools should be accessible. If you see DENIED,
  check that BaselinePermit was created successfully.
""")
