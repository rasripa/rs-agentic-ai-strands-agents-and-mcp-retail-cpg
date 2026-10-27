from strands import Agent

agent = Agent(model="us.anthropic.claude-haiku-4-5-20251001-v1:0", system_prompt="You are a helpful assistant that provides concise answers. ")
print(agent("Tell me about agentic AI"))

