# Lab 7: Agent registry

Registering an agent's tools so they can be discovered rather than hard-coded.

`agent-registry.py` connects to an AgentCore Gateway over streamable HTTP MCP, authenticating with
a Cognito access token read from SSM Parameter Store, and works with a registry record describing
the available tools.

## Before you run it

Two values must be set:

- **`registry_id`** — currently `'<your-registry-id>'` in the script. Take it from the registry's
  detail page in the console.
- **`gateway_token`** — read from SSM at `anycomp_agcore_gw_cognito_accesstoken`. The earlier
  gateway lab must have created it.

```bash
python agent-registry.py
```

## Why this matters

Hard-coding tool definitions into an agent couples the agent to its tools: every change to the
toolset is a code change and a redeploy. A registry inverts that — the agent asks what's available
at runtime, so tools can be added, removed or re-scoped without touching the agent. It's the same
principle as the A2A agent-card discovery in Lab 5, applied one level down.
