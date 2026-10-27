import boto3
import json
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

region = boto3.Session().region_name
ssm = boto3.client('ssm', region_name=region)

# registry_id is provided by the user (from the registry's console detail page)
registry_id = '<your-registry-id>'
record_name = 'anycomp-prod-reviews-record'
gateway_token = ssm.get_parameter(
    Name='anycomp_agcore_gw_cognito_accesstoken'
)['Parameter']['Value']

# Registry MCP endpoint — note singular "/registry/" (not "/registries/")
registry_mcp_url = (
    f"https://bedrock-agentcore.{region}.amazonaws.com"
    f"/registry/{registry_id}/mcp"
)

mcp_client = MCPClient(
    lambda: streamablehttp_client(
        registry_mcp_url,
        headers={"Authorization": f"Bearer {gateway_token}"},
    )
)

with mcp_client:
    # The registry MCP endpoint exposes a single tool, search_registry_records.
    # Invoke it; the PENDING gate filters the *records* returned, not the tool list.
    # The `filter` argument pins the match to an exact record name — without it
    # `searchQuery` does a fuzzy / semantic match and may surface other records.
    result = mcp_client.call_tool_sync(
        tool_use_id="search-demo",
        name="search_registry_records",
        arguments={
            "searchQuery": record_name,
            "filter": {"name": {"$eq": record_name}},
        },
    )

    records = []
    for block in result.get("content", []):
        text = block.get("text", "")
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            records = parsed
        elif isinstance(parsed, dict) and "records" in parsed:
            records = parsed["records"]

    print(f"search_registry_records returned {len(records)} record(s)")
    for r in records:
        print(f"  - {r.get('name')} (status={r.get('status')})")