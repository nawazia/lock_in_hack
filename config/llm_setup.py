# llm_setup.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm_openai():
    """Get OpenAI ChatGPT LLM (default)."""
    return ChatOpenAI(
        model="gpt-4o-mini",  # or another OpenAI model
        temperature=0.2,
    )

def get_llm_bedrock():
    """Get AWS Bedrock LLM (requires TEAM_ID and API_TOKEN in .env)."""
    from config.BedrockProxyLLM import BedrockProxyLLM
    return BedrockProxyLLM()

def get_llm(provider: str = None):
    """Get LLM based on provider or LLM_PROVIDER env var.

    Args:
        provider: 'openai' or 'bedrock'. If None, uses LLM_PROVIDER env var (defaults to 'openai')

    Returns:
        Configured LLM instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "bedrock":
        return get_llm_bedrock()
    else:  # default to openai
        return get_llm_openai()
