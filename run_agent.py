# run_agent.py
from lock_in_hack.agents.test_agent import build_agent

if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke({"input": "Hello! can you use your valyu search to seach online for cats?"})
    print("Final result:\n", result)
