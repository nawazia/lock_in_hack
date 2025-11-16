# LLM API Cost Comparison

This document explains the **LLM API cost differences** between optimization modes. This is about AI processing costs, NOT travel expenses.

## Model Pricing (Approximate)

Based on typical pricing for Claude models via OpenRouter:

| Model | Input Cost | Output Cost | Speed | Best For |
|-------|-----------|-------------|-------|----------|
| Claude 3.5 Haiku | $0.25/M tokens | $1.25/M tokens | Fast | Simple tasks, low cost |
| Claude 3.7 Sonnet | $3.00/M tokens | $15.00/M tokens | Medium | Balanced performance |
| Claude 3.7 Sonnet Thinking | $3.00/M tokens | $15.00/M tokens | Slower | Complex reasoning |

## Cost Optimization Modes

### Cost Mode (Minimum LLM Costs) 💰
**Uses: Claude 3.5 Haiku everywhere**

For a typical travel planning session:
- Interface Agent: ~500 tokens → $0.0004
- Flight Agent: ~1000 tokens → $0.0008
- Hotel Agent: ~1000 tokens → $0.0008
- Activities Agent: ~800 tokens → $0.0006
- Itinerary Agent: ~1200 tokens → $0.001

**Total Estimated Cost: ~$0.003 - $0.01 per session**

### Default Mode (Smart Selection) ⚖️
**Uses: Claude 3.7 Sonnet for most agents, Haiku for simple tasks**

For a typical travel planning session:
- Interface Agent: Sonnet → $0.0045
- Flight Agent: Sonnet → $0.009
- Hotel Agent: Sonnet → $0.009
- Activities Agent: Sonnet → $0.007
- Itinerary Agent: Sonnet → $0.011

**Total Estimated Cost: ~$0.04 - $0.08 per session**

### Latency Mode (Maximum Performance) ⚡
**Uses: Claude 3.7 Sonnet Thinking everywhere**

For a typical travel planning session:
- All agents use the most powerful model
- Extended thinking time for each decision
- Higher token usage due to reasoning traces

**Total Estimated Cost: ~$0.05 - $0.12 per session**

## Cost Savings Example

If you process 1000 travel planning sessions per month:

| Mode | Cost per Session | Monthly Cost | Annual Cost |
|------|-----------------|--------------|-------------|
| **Cost Mode** | $0.01 | $10 | $120 |
| **Default Mode** | $0.06 | $60 | $720 |
| **Latency Mode** | $0.10 | $100 | $1,200 |

**Potential savings: $600 - $1,080 per year by using Cost mode!**

## When to Use Each Mode

### Use Cost Mode When:
- ✅ You have high volume (1000s of requests per day)
- ✅ Tasks are relatively straightforward
- ✅ Budget is tight
- ✅ Response quality is acceptable with smaller models
- ✅ You want predictable, low costs

### Use Default Mode When:
- ✅ You want balanced performance and cost
- ✅ Different agents have different complexity needs
- ✅ Quality matters but cost is still a concern
- ✅ You trust the system to make smart choices

### Use Latency Mode When:
- ✅ Speed and quality are critical
- ✅ Cost is not a primary concern
- ✅ You need the best possible results
- ✅ Complex reasoning is required
- ✅ You're processing critical/high-value requests

## Real-World Impact

### Startup with Limited Budget
- **Scenario**: 500 travel queries per month
- **Recommendation**: Cost mode
- **Monthly Savings**: $25-50 compared to Latency mode
- **Annual Savings**: $300-600

### Enterprise with High Volume
- **Scenario**: 10,000 travel queries per month
- **Recommendation**: Default mode (balanced)
- **Monthly Cost**: ~$600
- **Benefit**: Smart allocation - simple tasks get cheap models, complex tasks get powerful models

### Premium Service
- **Scenario**: 1,000 high-value travel queries per month
- **Recommendation**: Latency mode
- **Monthly Cost**: ~$100
- **Benefit**: Best results, fastest response times, happy customers

## How This Works Technically

The `dynamic_model_router` selects models based on:

1. **Agent Requirements**: Autonomy, complexity, safety, reasoning needs
2. **User Preference**: Cost, latency, carbon, or automatic
3. **Smart Matching**: Ensures agents get models that meet their needs

### Example: Flight Agent

**Agent Requirements:**
- Moderate reasoning (search query construction)
- API integration complexity
- Medium risk (external data validation)

**Model Selection by Mode:**
- **Cost**: Haiku (sufficient for structured API calls)
- **Default**: Sonnet (better for complex searches)
- **Latency**: Sonnet Thinking (overkill but fastest/most accurate)

## Monitoring Your Costs

To track actual costs:

1. Check OpenRouter dashboard for usage
2. Look for log messages like:
   ```
   INFO - Interface agent initialized with model strategy: min
   ```
3. Count the API calls per agent
4. Multiply by approximate token usage

## Summary

**The optimization preference controls LLM API costs, not travel costs:**
- **Travel Budget** ($3000) → Handled by Budget Agent → Filters flights/hotels
- **LLM Cost Optimization** (Cost/Latency/Default) → Handled by Model Router → Selects AI models

Choose based on your volume, budget, and quality requirements!
