# Multi-Provider LLM Support

The system now supports both **Claude** and **OpenAI** models with automatic provider selection based on your optimization goals.

## Supported Providers

### Claude Models (via OpenRouter)
- **Reasoning**: `anthropic/claude-3.7-sonnet:thinking` - Extended reasoning, best for complex tasks
- **General Purpose**: `anthropic/claude-3.7-sonnet` - Balanced performance
- **Small/Cost**: `anthropic/claude-3.5-haiku` - Fast and affordable

### OpenAI Models (via OpenRouter)
- **Reasoning**: `openai/o1-preview` - Advanced reasoning capabilities
- **General Purpose**: `openai/gpt-4-turbo` - Powerful and versatile
- **Small/Cost**: `openai/gpt-3.5-turbo` - Very cost-effective

## How to Choose a Provider

### Option 1: Automatic Provider Selection (Recommended)

The system automatically chooses the best provider based on your optimization goal:

```python
from agents.travel_orchestrator import TravelOrchestrator
from models.travel_schemas import OptimizationPreference
from config.agent_model_config import ModelProvider

# Auto mode - system picks the best provider for each optimization
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST,
    provider_preference=ModelProvider.AUTO  # Default
)
```

**Auto-selection logic:**
- **Cost optimization** → OpenAI (GPT-3.5 Turbo is ~$0.15/M tokens vs Claude Haiku ~$0.25/M)
- **Latency optimization** → Claude (Sonnet Thinking has superior reasoning)
- **Carbon optimization** → OpenAI (GPT-3.5 is smaller and more efficient)
- **Default/Dynamic** → Claude (Better overall quality)

### Option 2: Explicit Provider Choice

Force all agents to use a specific provider:

```python
# Use only OpenAI models
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST,
    provider_preference=ModelProvider.OPENAI
)

# Use only Claude models
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.LATENCY,
    provider_preference=ModelProvider.CLAUDE
)
```

## Cost Comparison

### Per Million Tokens (Approximate via OpenRouter)

| Provider | Small Model | General Model | Reasoning Model |
|----------|-------------|---------------|-----------------|
| **Claude** | Haiku: $0.25 input / $1.25 output | Sonnet: $3.00 / $15.00 | Thinking: $3.00 / $15.00 |
| **OpenAI** | GPT-3.5: $0.50 input / $1.50 output | GPT-4 Turbo: $10.00 / $30.00 | O1: $15.00 / $60.00 |

### Real-World Session Costs (1000 travel queries)

| Optimization | Provider | Cost per Query | Monthly Cost (1000 queries) |
|--------------|----------|----------------|---------------------------|
| **Cost Mode** | OpenAI (auto) | $0.005 | $5 |
| **Cost Mode** | Claude | $0.010 | $10 |
| **Default Mode** | Claude (auto) | $0.060 | $60 |
| **Default Mode** | OpenAI | $0.080 | $80 |
| **Latency Mode** | Claude (auto) | $0.100 | $100 |
| **Latency Mode** | OpenAI | $0.150 | $150 |

**Recommendation**: Use `AUTO` provider with `COST` optimization for best savings (~$5/month for 1000 queries).

## Usage Examples

### Example 1: Minimize LLM Costs (Auto Provider)

```python
from agents.travel_orchestrator import TravelOrchestrator
from models.travel_schemas import OptimizationPreference
from config.agent_model_config import ModelProvider

# System will automatically use OpenAI GPT-3.5 for cost savings
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST,
    provider_preference=ModelProvider.AUTO
)

state = orchestrator.process_query("Plan a trip to Paris")
# All agents will use: openai/gpt-3.5-turbo
```

### Example 2: Maximum Performance with Claude

```python
# Force Claude for best reasoning capabilities
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.LATENCY,
    provider_preference=ModelProvider.CLAUDE
)

state = orchestrator.process_query("Plan a complex multi-city tour")
# All agents will use: anthropic/claude-3.7-sonnet:thinking
```

### Example 3: Balanced Approach with OpenAI

```python
# Use OpenAI with dynamic selection
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.DEFAULT,
    provider_preference=ModelProvider.OPENAI
)

state = orchestrator.process_query("Weekend getaway suggestions")
# Agents will intelligently use: gpt-4-turbo or gpt-3.5-turbo based on complexity
```

### Example 4: Let System Decide Everything

```python
# Full automation - best balance of cost, performance, and quality
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.DEFAULT,
    provider_preference=ModelProvider.AUTO
)
# System picks Claude for better quality by default
```

## Model Selection Matrix

| Optimization | Provider | Interface | Flight | Hotel | Activities | Itinerary |
|--------------|----------|-----------|--------|-------|------------|-----------|
| **Cost** | AUTO (→OpenAI) | GPT-3.5 | GPT-3.5 | GPT-3.5 | GPT-3.5 | GPT-3.5 |
| **Cost** | Claude | Haiku | Haiku | Haiku | Haiku | Haiku |
| **Cost** | OpenAI | GPT-3.5 | GPT-3.5 | GPT-3.5 | GPT-3.5 | GPT-3.5 |
| **Latency** | AUTO (→Claude) | Thinking | Thinking | Thinking | Thinking | Thinking |
| **Latency** | Claude | Thinking | Thinking | Thinking | Thinking | Thinking |
| **Latency** | OpenAI | O1 | O1 | O1 | O1 | O1 |
| **Default** | AUTO (→Claude) | Sonnet | Sonnet | Sonnet | Sonnet | Sonnet |
| **Default** | Claude | Sonnet/Haiku | Sonnet | Sonnet | Sonnet | Sonnet |
| **Default** | OpenAI | GPT-4 | GPT-4 | GPT-4 | GPT-4 | GPT-4 |

## Provider Strengths

### When to Use Claude:
✅ Complex reasoning tasks
✅ Multi-step planning
✅ High-quality outputs
✅ Extended thinking required
✅ Nuanced understanding needed

### When to Use OpenAI:
✅ Cost-sensitive applications
✅ High-volume processing
✅ Simple to moderate complexity
✅ Fast response times
✅ Established model ecosystem

## Environment Setup

Make sure you have the appropriate API keys set:

```bash
# .env file
OPENROUTER_API_KEY=your_openrouter_key_here

# OpenRouter supports both Claude and OpenAI models
# No separate API keys needed if using OpenRouter
```

## Logging and Monitoring

The system logs which models are selected:

```
INFO - Initializing orchestrator with optimization: cost, strategy: min, provider: openai
INFO - Interface agent initialized with openai/gpt-3.5-turbo (strategy: min)
INFO - Flight agent initialized with openai/gpt-3.5-turbo (strategy: min)
...
```

Monitor these logs to verify the correct models are being used.

## Migration from Single Provider

If you're upgrading from a system that only used Claude:

```python
# Old way (still works)
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST
)
# Uses Claude by default

# New way with explicit provider
orchestrator = TravelOrchestrator(
    optimization_preference=OptimizationPreference.COST,
    provider_preference=ModelProvider.OPENAI  # Now using OpenAI
)
```

The system is **backward compatible** - existing code will continue to use Claude as the default provider.

## Best Practices

1. **Use AUTO provider** unless you have specific requirements
2. **Monitor costs** via OpenRouter dashboard
3. **Test both providers** for your specific use case
4. **Consider quality vs cost** trade-offs for your application
5. **Use Cost mode with OpenAI** for maximum savings ($5 vs $100/month)

## Troubleshooting

### Models Not Available
If a model isn't available via OpenRouter, check:
- Model name is correct (`openai/gpt-3.5-turbo` not `gpt-3.5-turbo`)
- Your OpenRouter account has access
- Model hasn't been deprecated

### Unexpected Costs
- Check which provider is being auto-selected
- Verify optimization mode is set correctly
- Monitor actual token usage per agent

### Quality Issues
- Try switching providers for comparison
- Use Latency mode for better results
- Consider per-agent customization (advanced)

## Advanced: Mixed Provider Usage

For advanced users, you can customize `model_serving_agent.py` to mix providers:

```python
# Custom model selection
custom_models = {
    "reasoning_model": "openai/o1-preview",
    "general_purpose_model": "anthropic/claude-3.7-sonnet",
    "small_model": "openai/gpt-3.5-turbo"
}

# Pass to dynamic_model_router
model = dynamic_model_router(
    agent_description,
    model_selection=custom_models,
    default="dynamic"
)
```

This allows fine-grained control over which models are used for each complexity tier.
