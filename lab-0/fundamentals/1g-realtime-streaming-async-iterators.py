import asyncio
from strands import Agent
from strands_tools import calculator

async_iter_agent = Agent(
    tools=[calculator],
    callback_handler=None  # Disable default callback handler
)

# Async function that iterates over streamed agent events
async def process_streaming_response():
    query = "What is 25 * 48 and explain the calculation"

    # Get an async iterator for the agent's response stream
    agent_stream = async_iter_agent.stream_async(query)

    # Process events as they arrive
    async for event in agent_stream:
        # print(event)  # OPTIONAL:: uncomment this print statement to display detailed event trace
        if "data" in event:
            # Print text chunks as they're generated
            print(event["data"], end="", flush=True)
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            # Print tool usage information
            print(f"\n[Tool use delta for: {event['current_tool_use']['name']}]")

    ## Run the agent with the async event processing ##
    # Use below code to invoke agent from Jupyter notebook. 
    # Comment this await statement and uncomment aysncio.run(), if you are not executing this script in a Jupyter notebook.
    # await process_streaming_response()

# Uncomment below statement if using in a python file. asyncio.run () fails in Jupyter notebook. 
asyncio.run(process_streaming_response()) 