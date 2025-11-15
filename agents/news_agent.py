from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent

from lock_in_hack.tools.agent_tools import search_docs, valyu_search_tool 
from lock_in_hack.config.llm_setup import get_llm_openrouter  # or get_llm_openrouter

load_dotenv()

def build_agent():
    # 1. LLM
    llm = get_llm_openrouter()  # or get_llm_openrouter()

    # 2. Tools: note search_docs is already a Tool (because of @tool)
    tools = [search_docs, valyu_search_tool]

    # 3. Prompt – MUST include agent_scratchpad
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant. "
                "You can call tools to look things up when needed."
            ),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    # 4. Build the underlying agent
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    # 5. Wrap in an executor – this is the thing you call
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
    )

    return executor
