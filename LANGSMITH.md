# LangSmith Integration Guide

LangSmith provides powerful tracing and observability for the multi-agent news system.

## What is LangSmith?

LangSmith is LangChain's platform for debugging, testing, evaluating, and monitoring LLM applications. It provides:

- **Tracing**: See every LLM call, agent decision, and tool execution
- **Debugging**: Identify errors and bottlenecks quickly
- **Monitoring**: Track costs, latency, and performance
- **Evaluation**: Test and compare different prompts and models

## Setup

### 1. Get API Key

1. Go to [https://smith.langchain.com](https://smith.langchain.com)
2. Sign up or log in
3. Navigate to Settings → API Keys
4. Create a new API key

### 2. Configure Environment

Add to your `.env` file:

```bash
# Enable LangSmith tracing
LANGSMITH_ENABLED=true

# Add your API key
LANGSMITH_API_KEY=ls-your-api-key-here

# Optional: Custom project name
LANGSMITH_PROJECT=my-news-agent

# Optional: Custom endpoint (for self-hosted)
# LANGSMITH_ENDPOINT=https://smith.langchain.com
```

### 3. Install Dependencies

```bash
pip install langsmith
```

### 4. Verify Setup

```bash
python verify_setup.py
```

You should see:
```
🔍 Checking LangSmith tracing...
  ✅ LANGSMITH_API_KEY: ls-xxxxx...
  ✅ Project: multi-agent-news
  ✅ Tracing URL: https://smith.langchain.com/o/default/projects/p/multi-agent-news
```

## Usage

Once configured, tracing happens automatically:

```bash
# Run with tracing
python run_agent.py

# Interactive CLI with tracing
python cli.py -q "What's happening with AI?"
```

You'll see:
```
📊 LangSmith tracing enabled
   View traces at: https://smith.langchain.com/o/default/projects/p/multi-agent-news
```

## What Gets Traced?

### Automatic Tracing

All LangChain components are automatically traced:
- **LLM calls**: Every call to Bedrock/OpenAI
- **Prompts**: Input prompts and completions
- **Chains**: LCEL chain execution
- **Vector store**: Similarity searches

### Custom Metadata

The system adds useful metadata to traces:

**Query-level metadata**:
- User query
- Agent types used
- System identifier

**Result metadata**:
- Search results count
- RAG results count
- Completed agents
- Error indicators

## Viewing Traces

### Dashboard

1. Go to your project URL (shown when you run the system)
2. View all runs in chronological order
3. Click any run to see detailed trace

### Run Details

Each trace shows:
- **Timeline**: Execution flow and timing
- **Inputs/Outputs**: What went in and came out
- **Metadata**: Custom tags and information
- **Costs**: Token usage and estimated costs
- **Errors**: Stack traces if anything failed

### Useful Views

**By Agent**:
- Filter by tags: `multi-agent`, `news-processing`
- Compare agent performance

**By Query**:
- Search for specific queries in metadata
- See how similar queries perform

**By Error**:
- Filter runs with errors
- Debug failed executions

## Advanced Usage

### Custom Run Names

```python
from utils.langsmith_setup import trace_run

with trace_run(
    run_name="custom_search",
    tags=["custom", "search"],
    metadata={"user_id": "123"}
):
    results = search_agent.search(query)
```

### Adding Metadata

```python
from utils.langsmith_setup import add_run_metadata

add_run_metadata({
    "user_id": "123",
    "priority": "high",
    "custom_field": "value"
})
```

### Adding Tags

```python
from utils.langsmith_setup import add_run_tags

add_run_tags(["production", "priority-customer"])
```

## Best Practices

### 1. Use Projects

Create separate projects for different environments:
```bash
# Development
LANGSMITH_PROJECT=news-agent-dev

# Production
LANGSMITH_PROJECT=news-agent-prod
```

### 2. Add Meaningful Tags

Tag runs for easy filtering:
- Environment: `production`, `staging`, `development`
- User type: `free-tier`, `premium`
- Priority: `high`, `normal`, `low`

### 3. Monitor Costs

LangSmith tracks token usage and costs:
- Check daily/weekly spending
- Compare costs across agents
- Optimize expensive operations

### 4. Set Up Alerts

Configure alerts for:
- High error rates
- Slow response times
- Cost thresholds
- Unusual patterns

### 5. Regular Reviews

Review traces weekly to:
- Identify bottlenecks
- Find error patterns
- Optimize prompts
- Improve performance

## Troubleshooting

### Traces Not Appearing

**Check environment variables**:
```python
import os
print(os.getenv("LANGCHAIN_TRACING_V2"))  # Should be "true"
print(os.getenv("LANGCHAIN_API_KEY"))     # Should be set
```

**Verify network**:
- Ensure you can reach https://smith.langchain.com
- Check firewall settings

### Missing Data

**Ensure langsmith package is installed**:
```bash
pip install langsmith
```

**Check logs**:
```bash
LOG_LEVEL=DEBUG python run_agent.py
```

### Authentication Errors

**Regenerate API key**:
1. Go to Settings → API Keys
2. Delete old key
3. Create new key
4. Update `.env`

## Privacy & Security

### Data Sent to LangSmith

LangSmith receives:
- Input prompts
- LLM completions
- Metadata and tags
- Error messages

### What NOT to Send

Avoid sending sensitive data:
- User passwords
- API keys
- Personal identification
- Financial information

### Disable for Sensitive Queries

```python
# Temporarily disable tracing
os.environ["LANGCHAIN_TRACING_V2"] = "false"
result = process_sensitive_query()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
```

## Example Trace

Here's what you'll see for a typical query:

```
Query: "What's happening with AI?"
  ├─ [search_node] News Search Agent (2.3s)
  │   └─ [tool] valyu_search_tool (2.1s)
  ├─ [rag_node] RAG Agent (0.8s)
  │   ├─ [embed] Generate embeddings (0.3s)
  │   └─ [retrieve] Vector similarity search (0.5s)
  ├─ [analysis_node] Analysis Agent (1.5s)
  │   └─ [llm] Bedrock Claude call (1.2s)
  └─ [summary_node] Summary Agent (3.2s)
      └─ [llm] Bedrock Claude call (3.0s)

Total: 7.8s | Tokens: 3,245 | Cost: $0.02
```

Click any node to see inputs, outputs, and timing details!

## Resources

- [LangSmith Documentation](https://docs.langchain.com/langsmith/home)
- [LangSmith Python Client](https://github.com/langchain-ai/langsmith-sdk)
- [Tracing Conceptual Guide](https://python.langchain.com/docs/concepts/observability)
- [Best Practices](https://docs.langchain.com/langsmith/best-practices)
