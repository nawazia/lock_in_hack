"""Adapter to make BedrockProxyLLM compatible with hallbayes library.

hallbayes expects backends to implement:
- chat_create(messages: List[Dict], **kwargs) -> response
- multi_choice(messages: List[Dict], n: int, **kwargs) -> List[ChoiceLike]

This adapter wraps BedrockProxyLLM to provide these interfaces.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class _ChoiceLikeMessage:
    """Mimics OpenAI choice message structure."""
    content: str


@dataclass
class _ChoiceLike:
    """Mimics OpenAI choice structure."""
    message: _ChoiceLikeMessage


class BedrockHallbayesAdapter:
    """Adapter to make BedrockProxyLLM compatible with hallbayes.

    This adapter wraps a BedrockProxyLLM instance and provides the
    chat_create and multi_choice interfaces expected by hallbayes.
    """

    def __init__(self, bedrock_llm):
        """Initialize adapter with a BedrockProxyLLM instance.

        Args:
            bedrock_llm: An instance of BedrockProxyLLM
        """
        self.bedrock_llm = bedrock_llm
        self.model = getattr(bedrock_llm, 'model_name', 'bedrock-proxy')

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert hallbayes-style messages to a single prompt string.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Formatted prompt string
        """
        # Extract system and user messages
        system_parts = []
        user_parts = []

        for msg in messages:
            role = msg.get('role', '').lower()
            content = msg.get('content', '')

            if role == 'system':
                system_parts.append(content)
            elif role == 'user':
                user_parts.append(content)

        # Combine into a single prompt
        prompt_parts = []
        if system_parts:
            prompt_parts.append("System: " + "\n\n".join(system_parts))
        if user_parts:
            prompt_parts.append("User: " + "\n\n".join(user_parts))

        return "\n\n".join(prompt_parts)

    def chat_create(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Single chat completion call.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Response object with choices[0].message.content
        """
        prompt = self._messages_to_prompt(messages)

        # Update max_tokens if provided in kwargs
        if 'max_tokens' in kwargs:
            # Temporarily override max_tokens
            original_max_tokens = self.bedrock_llm.max_tokens
            self.bedrock_llm.max_tokens = kwargs['max_tokens']
            try:
                response_text = self.bedrock_llm._call(prompt)
            finally:
                self.bedrock_llm.max_tokens = original_max_tokens
        else:
            response_text = self.bedrock_llm._call(prompt)

        # Return a mock response object
        return _ChoiceLike(_ChoiceLikeMessage(response_text))

    def multi_choice(self, messages: List[Dict[str, str]], n: int = 1, **kwargs) -> List[_ChoiceLike]:
        """Generate n independent completions for the same prompt.

        Args:
            messages: List of message dicts
            n: Number of completions to generate
            **kwargs: Additional parameters

        Returns:
            List of n choice-like objects with message.content
        """
        choices = []

        for i in range(n):
            try:
                choice = self.chat_create(messages, **kwargs)
                choices.append(choice)
                logger.debug(f"Generated completion {i+1}/{n}")
            except Exception as e:
                logger.error(f"Error generating completion {i+1}/{n}: {e}")
                # Return a fallback choice
                choices.append(_ChoiceLike(_ChoiceLikeMessage("refuse")))

        return choices


def create_bedrock_adapter(bedrock_llm):
    """Factory function to create a BedrockHallbayesAdapter.

    Args:
        bedrock_llm: BedrockProxyLLM instance

    Returns:
        BedrockHallbayesAdapter instance compatible with hallbayes
    """
    return BedrockHallbayesAdapter(bedrock_llm)
