import os
import requests
import json
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from langchain_core.language_models import LLM
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv() 

class BedrockProxyLLM(LLM, BaseModel):
    """Custom LLM class for the Holistic AI Bedrock Proxy API."""
    
    # 1. Define Model Parameters
    team_id: str = Field(default_factory=lambda: os.getenv("TEAM_ID"))
    api_token: str = Field(default_factory=lambda: os.getenv("API_TOKEN"))
    api_endpoint: str = Field(default_factory=lambda: os.getenv("API_ENDPOINT", "https://ctwa92wg1b.execute-api.us-east-1.amazonaws.com/prod/invoke"))
    model_name: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0" #
    max_tokens: int = 1024 #

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

        headers = {
            "Content-Type": "application/json",
            "X-Team-ID": self.team_id,
            "X-API-Token": self.api_token
        }

        # The proxy API expects the prompt within a 'messages' array (Anthropic format)
        payload = {
            "team_id": self.team_id,
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens
        }

        try:
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