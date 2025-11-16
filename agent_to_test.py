from model_serving_agent import dynamic_model_router
from config.llm_setup import get_llm_openrouter

prompt = """
This agent analyzes multi-step workflows in project plans, identifies blockers, and proposes optimized task sequences.
It uses a timeline parser tool and a dependency-graph API. Some planning and multi-step reasoning are required.
"""


# print(dynamic_model_router(prompt))

from langchain_core.messages import AIMessage
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent_prompt = """
weather agent
you are a helpful assistant. 
you can get the weather using the get_weather tool"""

llm = get_llm_openrouter(model=dynamic_model_router(agent_prompt, default="max"))

agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt=agent_prompt,
)

# Run the agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello! can you use your valyu search to seach online for cats?"}]}
)

final_message = result.get("messages")[-1] if result.get("messages") else None

# Check if the final message is an AIMessage (the agent's final answer) and print its content
if isinstance(final_message, AIMessage):
    print("Agent Final Output:")
    print(final_message.content)
else:
    # If the output structure is different (e.g., just a string or dict), you may need to adjust this.
    print("Agent Result Dictionary:")
    print(result)

print("done")
print(llm)