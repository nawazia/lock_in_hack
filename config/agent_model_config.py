"""Configuration for agent model selection and descriptions.

This module contains:
1. Detailed descriptions of each agent's requirements for the dynamic_model_router
2. Mapping from optimization preferences to model selection strategies
3. Provider selection (Claude vs OpenAI)
"""

from models.travel_schemas import OptimizationPreference
from enum import Enum


class ModelProvider(str, Enum):
    """LLM provider preference."""
    CLAUDE = "claude"
    OPENAI = "openai"
    AUTO = "auto"  # Automatically select best provider for each optimization mode


# Agent descriptions for dynamic_model_router
# These descriptions help the model_serving_agent determine the appropriate LLM
AGENT_DESCRIPTIONS = {
    "interface": """
Interface Agent for travel planning.
Extracts structured information from natural language user queries about travel preferences.
Uses JSON output parsing to extract budget, timeframe, locations, interests, and activities.
Generates clarifying questions when information is missing.
Moderate complexity with structured output requirements.
Requires good reasoning to understand user intent and context from conversation history.
Low risk - no external actions, only information extraction.
    """.strip(),

    "flight": """
Flight Search Agent for travel planning.
Searches for flights using the Valyu search API based on travel intent.
Parses search results and structures flight information (airline, times, prices).
Moderate tool complexity with API calls and result parsing.
Requires reasoning to construct effective search queries and filter results.
Medium risk - relies on external API data that needs validation.
    """.strip(),

    "hotel": """
Hotel Search Agent for travel planning.
Searches for hotels using the Valyu search API based on location and preferences.
Parses search results and structures hotel information (name, location, price, amenities).
Moderate tool complexity with API calls and result parsing.
Requires reasoning to match hotels to user preferences and filter results.
Medium risk - relies on external API data that needs validation.
    """.strip(),

    "budget": """
Budget Matching Agent for travel planning.
Analyzes flights and hotels to create combinations that fit within user's budget constraints.
Performs calculations and optimization to maximize value within budget.
Simple deterministic task with mathematical operations.
Low complexity - primarily arithmetic and filtering logic.
Low risk - internal calculations only.
    """.strip(),

    "activities": """
Activities Search Agent for travel planning.
Searches for activities, experiences, and attractions using Valyu search API.
Matches activities to user interests (food, culture, adventure, etc.).
Moderate tool complexity with API calls and result parsing.
Requires reasoning to understand user interests and find relevant activities.
Medium risk - relies on external API data that needs validation.
    """.strip(),

    "ranking": """
Ranking Agent for travel planning.
Ranks travel option bundles (flight + hotel + activities) based on multiple criteria.
Evaluates budget fit, preference alignment, quality, and efficiency.
Requires moderate reasoning to balance multiple scoring dimensions.
Complex multi-criteria decision making with scoring algorithms.
Medium risk - recommendations affect user's travel decisions.
    """.strip(),

    "itinerary": """
Itinerary Creation Agent for travel planning.
Creates detailed day-by-day travel itineraries from ranked options.
Structures activities across days, adds packing suggestions and travel tips.
Requires planning and organization skills to create coherent schedules.
Moderate reasoning depth for logical daily planning and sequencing.
Medium risk - creates actionable travel plans users will follow.
    """.strip(),

    "audit": """
Audit Agent for travel planning.
Validates final itinerary for logical errors, inconsistencies, and data quality issues.
Checks for date conflicts, missing information, price discrepancies, and practicality.
Requires high reasoning depth to identify subtle errors and edge cases.
Safety-critical role - catches errors that could ruin user's trip.
High risk - final quality gate before presenting to user.
    """.strip(),
}


# Mapping from optimization preference to model_serving_agent's `default` parameter
OPTIMIZATION_TO_MODEL_STRATEGY = {
    OptimizationPreference.DEFAULT: "mid",  # Use medium model for balanced performance
    OptimizationPreference.LATENCY: "max",      # Use largest/fastest model for all agents
    OptimizationPreference.COST: "min",         # Use smallest/cheapest model for all agents
    OptimizationPreference.CARBON: "min",       # Use smallest model for lowest carbon footprint
}

# Force certain agents to use minimum model tier regardless of user preference
# This ensures critical agents like interface work properly
AGENT_MIN_MODEL_TIER = {
    "interface": "mid",  # Interface agent needs at least mid-tier for JSON extraction
    "audit": "mid",      # Audit agent needs good reasoning to catch errors
}


def get_model_strategy(optimization_preference: OptimizationPreference, agent_name: str = None) -> str:
    """Convert optimization preference to model selection strategy.

    Args:
        optimization_preference: User's optimization preference
        agent_name: Optional agent name to apply minimum tier requirements

    Returns:
        Model strategy string for dynamic_model_router's `default` parameter
    """
    base_strategy = OPTIMIZATION_TO_MODEL_STRATEGY.get(
        optimization_preference,
        "mid"  # Fallback to mid
    )

    # If agent has a minimum tier requirement, use the higher of the two
    if agent_name and agent_name in AGENT_MIN_MODEL_TIER:
        min_tier = AGENT_MIN_MODEL_TIER[agent_name]

        # Define tier hierarchy
        tier_hierarchy = {"min": 0, "mid": 1, "max": 2}

        base_tier_level = tier_hierarchy.get(base_strategy, 1)
        min_tier_level = tier_hierarchy.get(min_tier, 1)

        if min_tier_level > base_tier_level:
            return min_tier

    return base_strategy


def get_provider_for_optimization(
    optimization_preference: OptimizationPreference,
    user_provider_preference: ModelProvider = ModelProvider.AUTO
) -> str:
    """Determine which model provider to use based on optimization preferences.

    Args:
        optimization_preference: User's optimization preference
        user_provider_preference: User's provider preference (claude, openai, or auto)

    Returns:
        Provider string ("claude", "openai", or "auto")
    """
    # If user explicitly chose a provider, respect that
    if user_provider_preference in [ModelProvider.CLAUDE, ModelProvider.OPENAI]:
        return user_provider_preference.value

    # Auto-select based on optimization goal
    if optimization_preference == OptimizationPreference.COST:
        # OpenAI GPT-3.5 Turbo is cheaper than Claude Haiku
        return "openai"
    elif optimization_preference == OptimizationPreference.LATENCY:
        # Claude Sonnet Thinking has extended reasoning capabilities
        return "claude"
    elif optimization_preference == OptimizationPreference.CARBON:
        # OpenAI GPT-3.5 is smaller and more efficient
        return "openai"
    else:
        # Default mode - use Claude for better overall quality
        return "claude"
