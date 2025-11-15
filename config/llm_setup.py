# llm_setup.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm_openai():
    return ChatOpenAI(
        model="gpt-4o-mini",  # or another OpenAI model
        temperature=0.2,
    )

def get_llm_openrouter():
    return ChatOpenAI(
        model="anthropic/claude-3.5-sonnet",  # OpenRouter model slug
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )
