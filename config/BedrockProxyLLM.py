import os
import requests
import json
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from langchain_core.language_models import LLM
from dotenv import load_dotenv

# Load credentials from .env FIRST
load_dotenv()

# Get environment variables immediately (evaluated once at import time)
_TEAM_ID = os.getenv("TEAM_ID", "")
_API_TOKEN = os.getenv("API_TOKEN", "")
_API_ENDPOINT = os.getenv("API_ENDPOINT", "https://ctwa92wg1b.execute-api.us-east-1.amazonaws.com/prod/invoke")

class BedrockProxyLLM(LLM, BaseModel):
    """Custom LLM class for the Holistic AI Bedrock Proxy API."""

    # 1. Define Model Parameters - use module-level variables as defaults
    team_id: str = _TEAM_ID
    api_token: str = _API_TOKEN
    api_endpoint: str = _API_ENDPOINT
    model_name: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    max_tokens: int = 1024

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Returns the type of LLM."""
        return "bedrock_proxy"

    # 2. Implement the core API call method
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
    ) -> str:
        """The main method to call the LLM API."""

        # Debug: Log what we're using
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"BedrockProxyLLM using team_id={self.team_id[:10]}..., has_token={bool(self.api_token)}, endpoint={self.api_endpoint}")

        headers = {
            "Content-Type": "application/json",
            "X-Team-ID": self.team_id,
            "X-API-Token": self.api_token
        }

        # The proxy API expects the prompt within a 'messages' array (Anthropic format)
        payload = {
            "team_id": self.team_id,
            "api_token": self.api_token,  # Added: API token in payload too
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens
        }

        # Debug: Log the payload (without full token)
        logger.debug(f"Payload keys: {list(payload.keys())}, model={payload['model']}")
        logger.debug(f"Full payload (sanitized): {json.dumps({**payload, 'team_id': payload['team_id'][:10]+'...', 'api_token': '***'})}")

        try:
            logger.debug(f"POST to {self.api_endpoint}")
            response = requests.post(self.api_endpoint, headers=headers, json=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            # The guide shows the response text is in ['content'][0]['text']
            result = response.json()
            return result["content"][0]["text"]
        
        except requests.exceptions.HTTPError as e:
            # Handle specific errors like 401 Unauthorized or 429 Too Many Requests
            return f"API Error: {e}. Check credentials or quota. Response: {response.text}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"