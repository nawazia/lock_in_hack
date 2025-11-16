# llm_setup.py
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables first
load_dotenv()

# Initialize LangSmith tracing if configured
# This will automatically trace all LLM calls and tool executions
if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # These should already be set in .env, but we ensure they're loaded
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
    if os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
    if os.getenv("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")


def get_llm_openai():
    """Get OpenAI ChatGPT LLM (default)."""
    return ChatOpenAI(
        model="gpt-4o-mini",  # or another OpenAI model
        temperature=0.2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )


def get_llm_bedrock():
    """Get AWS Bedrock LLM (requires TEAM_ID and API_TOKEN in .env)."""
    from config.BedrockProxyLLM import BedrockProxyLLM

    return BedrockProxyLLM()


def get_llm(provider: str = None):
    """Get LLM based on provider or LLM_PROVIDER env var.

    Args:
        provider: 'openai' or 'bedrock'. If None, uses LLM_PROVIDER env var (defaults to 'bedrock')

    Returns:
        Configured LLM instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "bedrock").lower()

    if provider == "bedrock":
        return get_llm_bedrock()
    elif provider == "openai":
        return get_llm_openai()
    

def get_llm_openrouter(model="anthropic/claude-3.5-sonnet"):
    return ChatOpenAI(
        model=model,  # OpenRouter model slug
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )

