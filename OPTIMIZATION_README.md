# Dynamic LLM Optimization Feature

This feature enables users to choose what to optimize for when running the multi-agent travel planning system **in terms of LLM API costs and performance**. The system uses the `dynamic_model_router` from `model_serving_agent.py` to automatically select the best LLM for each agent based on both the agent's requirements and the user's optimization preferences.

## Overview

**IMPORTANT**: This optimizes the **cost of AI model API calls**, not the travel budget. The travel budget (e.g., $3000 for flights/hotels) is handled separately by the Budget Agent.

The system now asks users at the start of their session what they want to optimize for:

1. **Nothing (Default)** - Automatically selects the best model for each agent based on its specific requirements
2. **Latency** - Prioritizes speed and performance by using more powerful (expensive) models → **Higher API costs**
3. **Cost** - Minimizes LLM API call costs by using efficient smaller models → **Lower API bills**
4. **Carbon Emissions** - Minimizes environmental impact by using energy-efficient models

## How It Works

### 1. User Preference Collection

The **Interface Agent** (`agents/interface_agent.py`) asks users about their optimization preference at the start of the conversation:

```
Before we start planning your trip, what would you like to optimize for?

1. Nothing (default) - I'll automatically select the best AI models for each task
2. Latency - Prioritize speed and performance (uses more powerful models)
3. Cost - Minimize AI processing costs (uses efficient smaller models)
4. Carbon emissions - Minimize environmental impact (uses energy-efficient models)
```

Users can respond with keywords like "latency", "cost", "carbon", or "nothing"/"default".

### 2. Model Selection Strategy

The optimization preference is mapped to a model selection strategy in `config/agent_model_config.py`:

- **Default** → `"dynamic"` - Uses `dynamic_model_router` to analyze each agent's requirements
- **Latency** → `"max"` - Uses the largest/most capable model (Claude 3.7 Sonnet Thinking)
- **Cost** → `"min"` - Uses the smallest/most efficient model (Claude 3.5 Haiku)
- **Carbon** → `"min"` - Uses the smallest model for lowest carbon footprint (Claude 3.5 Haiku)

### 3. Dynamic Model Routing

For each agent, the system:

1. Provides a detailed description of the agent's requirements (autonomy, complexity, safety, reasoning, context)
2. Calls `dynamic_model_router(agent_description, default=strategy)` to select the appropriate model
3. Initializes the agent with the selected model

**Example for the Flight Agent:**

```python
flight_llm = get_llm_openrouter(
    model=dynamic_model_router(
        AGENT_DESCRIPTIONS["flight"],
        default=model_strategy  # "dynamic", "max", or "min"
    )
)
self.flight_agent = FlightAgent(llm=flight_llm)
```

### 4. Agent Descriptions

Each agent has a detailed description in `config/agent_model_config.py` that helps the `dynamic_model_router` understand its requirements:

```python
"flight": """
Flight Search Agent for travel planning.
Searches for flights using the Valyu search API based on travel intent.
Parses search results and structures flight information (airline, times, prices).
Moderate tool complexity with API calls and result parsing.
Requires reasoning to construct effective search queries and filter results.
Medium risk - relies on external API data that needs validation.
""".strip()
```

### 5. Dynamic Agent Reinitialization

The **Travel Orchestrator** (`agents/travel_orchestrator.py`) can reinitialize agents if the optimization preference changes during the conversation:

```python
def _reinitialize_agents_if_needed(self, new_preference: OptimizationPreference):
    """Reinitialize agents if optimization preference has changed."""
    if new_preference == self.optimization_preference:
        return

    # Reinitialize all agents with new model selection strategy
    ...
```

## Architecture Changes

### Modified Files

1. **`models/travel_schemas.py`**
   - Added `OptimizationPreference` enum
   - Added `optimization_preference` field to `TravelPlanningState`

2. **`config/agent_model_config.py`** (NEW)
   - Agent descriptions for dynamic model routing
   - Optimization-to-strategy mapping
   - Helper functions

3. **`agents/interface_agent.py`**
   - Added `extract_optimization_preference()` method
   - Modified `run()` to ask about optimization at the start
   - Handles optimization preference before travel intent extraction

4. **`agents/travel_orchestrator.py`**
   - Modified `__init__()` to accept `optimization_preference` parameter
   - Uses `dynamic_model_router` for each agent
   - Added `_reinitialize_agents_if_needed()` method
   - Updates `process_query()` to handle preference changes

5. **`test_optimization.py`** (NEW)
   - Demonstration and testing script
   - Shows model selection for different optimization modes

## Usage

### Running the System

```python
from agents.travel_orchestrator import TravelOrchestrator
from models.travel_schemas import OptimizationPreference

# Option 1: Let the interface agent ask the user
orchestrator = TravelOrchestrator()
state = orchestrator.process_query("I want to plan a trip to Paris")
# System will ask: "What would you like to optimize for?"

# Option 2: Specify optimization preference upfront
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST
)
state = orchestrator.process_query("Plan a budget trip to Paris")
```

### Testing the Feature

```bash
python test_optimization.py
```

This will:
1. Show the model selection logic
2. Demonstrate all optimization modes
3. Display which models are selected for each agent

### Example Flow

```
User: "I want to plan a trip to Hong Kong"

System: "Before we start planning your trip, what would you like to optimize for?
1. Nothing (default)
2. Latency
3. Cost
4. Carbon emissions"

User: "cost"

System: "Great! I'll optimize for cost. Now, tell me about your travel plans!"
[Interface Agent uses Claude 3.5 Haiku]
[Flight Agent uses Claude 3.5 Haiku]
[Hotel Agent uses Claude 3.5 Haiku]
...
```

## Model Selection Matrix

| Agent | Dynamic (Default) | Latency (Max) | Cost (Min) | Carbon (Min) |
|-------|-------------------|---------------|------------|--------------|
| Interface | Auto-selected | Claude 3.7 Sonnet Thinking | Claude 3.5 Haiku | Claude 3.5 Haiku |
| Flight | Auto-selected | Claude 3.7 Sonnet Thinking | Claude 3.5 Haiku | Claude 3.5 Haiku |
| Hotel | Auto-selected | Claude 3.7 Sonnet Thinking | Claude 3.5 Haiku | Claude 3.5 Haiku |
| Budget | N/A (deterministic) | N/A | N/A | N/A |
| Activities | Auto-selected | Claude 3.7 Sonnet Thinking | Claude 3.5 Haiku | Claude 3.5 Haiku |
| Ranking | N/A (deterministic) | N/A | N/A | N/A |
| Itinerary | Auto-selected | Claude 3.7 Sonnet Thinking | Claude 3.5 Haiku | Claude 3.5 Haiku |
| Audit | N/A (deterministic) | N/A | N/A | N/A |

**Note**: "Auto-selected" means the `dynamic_model_router` analyzes the agent's description and requirements to choose the most appropriate model from the available options.

## Benefits

1. **User Control** - Users can optimize for what matters most to them
2. **Cost Efficiency** - Save money by using smaller models when appropriate
3. **Performance** - Get better results by using larger models when needed
4. **Sustainability** - Reduce carbon footprint by choosing efficient models
5. **Flexibility** - System adapts to changing preferences during conversation
6. **Intelligent Selection** - In default mode, each agent gets the right model for its specific needs

## Future Enhancements

Potential improvements:

1. **Per-Agent Optimization** - Allow users to specify different optimization for different agents
2. **Hybrid Mode** - Mix strategies (e.g., use max for critical agents, min for others)
3. **Custom Strategies** - Let users define custom model selection rules
4. **Performance Metrics** - Track and display actual cost/latency/carbon for each run
5. **A/B Testing** - Compare results between different optimization strategies
6. **Learning** - Automatically adjust based on success metrics

## Technical Details

### Model Profiles

The `model_serving_agent.py` defines capability profiles for each model type:

```python
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
```

### Scoring Algorithm

When `default="dynamic"`, the `compare_llm_selection()` function:

1. Evaluates agent requirements against model capabilities
2. Penalizes models that fall short of requirements (shortfall² penalty)
3. Adds a small size bias to prefer smaller models when capabilities are equal
4. Selects the model with the lowest total score

This ensures agents get models that meet their needs without overprovisioning.

## Logging

The system logs model selection decisions:

```
INFO - Initializing orchestrator with optimization: cost, strategy: min
INFO - Interface agent initialized with model strategy: min
INFO - Flight agent initialized with model strategy: min
...
INFO - Optimization preference changed from default to cost
INFO - All agents reinitialized with strategy: min
```

Monitor these logs to verify correct model selection.
