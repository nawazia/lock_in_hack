import json
from langchain.agents import create_agent
from config.llm_setup import get_llm_openrouter

llm = get_llm_openrouter(model="anthropic/claude-3.5-haiku")

# Model selections by provider
model_selection_claude = {
    "reasoning_model": "anthropic/claude-3.7-sonnet:thinking",
    "general_purpose_model": "anthropic/claude-3.7-sonnet",
    "small_model": "anthropic/claude-3.5-haiku"
}

model_selection_openai = {
    "reasoning_model": "openai/o1-preview",  # Best reasoning
    "general_purpose_model": "openai/gpt-4-turbo",  # Balanced performance
    "small_model": "openai/gpt-3.5-turbo"  # Cost-effective
}

# Default to Claude (can be changed)
model_selection = model_selection_claude

model_size_rank = {
    "small_model": 0,            # most preferred
    "general_purpose_model": 1,  # middle
    "reasoning_model": 2         # least preferred
}

agent_model_selection_factors = {
    "autonomy_decision_scope": {
        "description": "How broad and independent the agent's responsibilities and decisions are.",
        "scale": {
            "0-1": "Very narrow tasks; single tool or deterministic flow; minimal decision-making.",
            "2-3": "Moderately open tasks; several tools; some branching logic; bounded autonomy.",
            "4-5": "Highly open-ended tasks; many tools; multi-step goal achievement; high autonomy."
        }
    },
    "tooling_environment_complexity": {
        "description": "How complex the agent's toolset, APIs, schemas, and environment are.",
        "scale": {
            "0-1": "No tools or one simple tool with low error modes.",
            "2-3": "Multiple tools with structured arguments, moderate complexity, potential errors.",
            "4-5": "Large toolset with complex schemas, side effects, multi-step APIs, or nested agents."
        }
    },
    "safety_error_tolerance": {
        "description": "How severe the consequences of agent mistakes are.",
        "scale": {
            "0-1": "Low-risk tasks; harmless errors (summaries, content generation).",
            "2-3": "Medium-risk tasks; business logic or external actions reviewed by humans.",
            "4-5": "High-risk tasks; legal, financial, infrastructure, or automation actions with real-world impact."
        }
    },
    "reasoning_requirement": {
        "description": "How deep, multi-step, or complex the reasoning chains must be for the agent to succeed.",
        "scale": {
            "0-1": "Simple tasks; direct responses; minimal reasoning; 1-2 step logic.",
            "2-3": "Moderate reasoning depth; multi-step thought; requires evaluating options or chaining steps.",
            "4-5": "High reasoning depth; long, branching, or advanced reasoning; planning; problem decomposition; meta-reasoning."
        }
    },
    "context_size_requirement": {
        "description": "How much context (memory, documents, logs, prior messages) the agent must handle at once.",
        "scale": {
            "0-1": "Very small context; short messages; minimal need for extended memory.",
            "2-3": "Moderate context windows; medium-length conversations, documents, or tool outputs.",
            "4-5": "Large context windows needed; long documents, multi-session history, or complex multi-agent logs."
        }
    }
}

model_profiles = {
    "reasoning_model": {
        "autonomy_decision_scope": 5,
        "tooling_environment_complexity": 5,
        "safety_error_tolerance": 5,
        "reasoning_requirement": 5,
        "context_size_requirement": 4
    },
    "general_purpose_model": {
        "autonomy_decision_scope": 4,
        "tooling_environment_complexity": 4,
        "safety_error_tolerance": 4,
        "reasoning_requirement": 3,
        "context_size_requirement": 5
    },
    "small_model": {
        "autonomy_decision_scope": 2,
        "tooling_environment_complexity": 2,
        "safety_error_tolerance": 2,
        "reasoning_requirement": 1,
        "context_size_requirement": 2
    }
}

from langchain_core.prompts import ChatPromptTemplate

system_prompt = f"""
You are evaluating an AI agent specification.
You must rate it on five dimensions, each from 0 to 5 (integers only). Use this spec:

{json.dumps(agent_model_selection_factors, indent=2)}

IMPORTANT:
- Respond with JSON ONLY.
- Do NOT include any explanation, comments, or additional text.
- Your response MUST be a single JSON object.

Return ONLY valid JSON shaped like:
{{
  "autonomy_decision_scope": 2,
  "tooling_environment_complexity": 2,
  "safety_error_tolerance": 2,
  "reasoning_requirement": 1,
  "context_size_requirement": 2
}}
"""

def estimate_agent_llm_req(agent_description: str) -> dict:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": agent_description},
    ]

    result = llm.invoke(messages)

    # Depending on your LLM wrapper, `result` may be a message object or a raw string
    content = getattr(result, "content", result)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse JSON from LLM: {content!r}")

    # Normalise + clamp
    clean = {}
    for k in agent_model_selection_factors.keys():
        v = int(parsed.get(k, 0))
        clean[k] = max(0, min(5, v))

    return clean


def compare_llm_selection(
    agent_llm_req: dict,
    model_profiles=model_profiles,
    model_size_rank=model_size_rank,
    size_bias: float = 0.2,
) -> str:
    """
    Choose the best model given agent_llm_req.

    Scoring:
    - For each metric, penalise only when the model is BELOW the requirement:
        shortfall = max(0, required - model_value)
        penalty += shortfall^2
    - Then add a small size bias term:
        total_score = penalty + size_bias * model_size_rank[model_name]

    The model with the smallest total_score is chosen.

    size_bias controls how strongly you prefer smaller models:
    - 0.0  -> no size preference
    - 0.1–0.3 -> mild preference for smaller
    - >0.5 -> strong preference for smaller
    """
    best_model = None
    best_score = float("inf")

    for model_name, profile in model_profiles.items():
        penalty = 0.0

        for metric, required_val in agent_llm_req.items():
            model_val = profile.get(metric, 0)
            shortfall = max(0, required_val - model_val)
            penalty += shortfall ** 2  # strong punishment for big gaps

        size_penalty = size_bias * model_size_rank.get(model_name, 1)
        total_score = penalty + size_penalty

        if total_score < best_score:
            best_score = total_score
            best_model = model_name

    return best_model


def dynamic_model_router(agent_description: str, model_profiles=model_profiles,
                         default="dynamic", model_selection=None, provider="claude") -> str:
    '''
    Takes in system prompt of agent and outputs a string of the model code to be input into the openrouter model caller.

    Args:
        agent_description: Description of the agent's requirements
        model_profiles: Capability profiles for model types
        default: Selection strategy ("dynamic", "max", "mid", "min")
        model_selection: Custom model selection dict (optional)
        provider: "claude", "openai", or "auto" to choose provider

    Returns:
        Model identifier string for OpenRouter (e.g., "anthropic/claude-3.5-haiku")

    Example:
        llm = get_llm_openrouter(model=dynamic_model_router(agent_prompt, provider="openai"))
    '''
    # Select provider-specific models if not provided
    if model_selection is None:
        if provider == "openai":
            model_selection = model_selection_openai
        elif provider == "claude":
            model_selection = model_selection_claude
        elif provider == "auto":
            # Auto-select based on default strategy
            # For cost optimization, prefer OpenAI (GPT-3.5 is cheaper than Haiku)
            # For reasoning, prefer Claude (Claude Thinking is better)
            if default == "min":
                model_selection = model_selection_openai  # GPT-3.5 is very cheap
            elif default == "max":
                model_selection = model_selection_claude  # Claude Thinking is best
            else:
                model_selection = model_selection_claude  # Default to Claude
        else:
            model_selection = model_selection_claude  # Fallback to Claude

    if default == "max":
        return model_selection["reasoning_model"]

    if default == "mid":
        return model_selection["general_purpose_model"]

    if default == "min":
        return model_selection["small_model"]

    if default == "dynamic":
        agent_requirements = estimate_agent_llm_req(agent_description)
        llm_type_choice = compare_llm_selection(agent_requirements, model_profiles)
        chosen_model = model_selection[llm_type_choice]
        return chosen_model

    return None


