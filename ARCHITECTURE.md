# System Architecture

## Overview

This multi-agent system follows best practices from LangChain and LangGraph to create a robust, scalable news processing pipeline.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                              │
│                     "What's new in AI?"                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                            │
│                    (LangGraph Workflow)                         │
│                                                                 │
│  • Manages agent state                                          │
│  • Coordinates workflow                                         │
│  • Handles errors                                               │
│  • Tracks completion                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐  ┌──────────┐  ┌──────────┐
    │   Search     │  │   RAG    │  │ Analysis │
    │   Agent      │→ │  Agent   │→ │  Agent   │
    └──────────────┘  └──────────┘  └──────────┘
                                            │
                                            ▼
                                     ┌──────────┐
                                     │ Summary  │
                                     │  Agent   │
                                     └──────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │Final Output  │
                                    └──────────────┘
```

## Component Details

### 1. Orchestrator Agent (`orchestrator.py`)

**Purpose**: Coordinates all agents using LangGraph

**Key Features**:
- Uses LangGraph's StateGraph for workflow definition
- Sequential execution: Search → RAG → Analysis → Summary
- Error handling at each node
- State management throughout the pipeline

**State Flow**:
```python
AgentState = {
    user_query: str,
    search_results: List[NewsArticle],
    rag_results: List[NewsArticle],
    analysis: str,
    summary: str,
    completed_agents: List[str],
    metadata: Dict[str, Any]
}
```

### 2. News Search Agent (`news_search_agent.py`)

**Purpose**: Search for news using external APIs

**Implementation**:
- Uses LangChain's `create_tool_calling_agent`
- Wraps Valyu search API as a LangChain tool
- Parses unstructured output into `NewsArticle` objects
- Max 3 iterations with retry logic

**Tools Used**:
- `valyu_search_tool`: Custom tool for Valyu API

**Output**: Structured list of `NewsArticle` objects

### 3. RAG Agent (`rag_agent.py`)

**Purpose**: Persistent storage and retrieval of news articles

**Technology Stack**:
- ChromaDB for vector storage
- OpenAI embeddings (`text-embedding-3-small`)
- Automatic persistence to disk

**Key Operations**:

1. **Store Articles**:
   - Chunks long articles
   - Creates embeddings
   - Stores in vector DB with metadata

2. **Retrieve Articles**:
   - Similarity search
   - Metadata filtering
   - Score-based ranking

**Storage Location**: `storage/chroma_db/`

### 4. Analysis Agent (`analysis_agent.py`)

**Purpose**: Analyze and select relevant articles

**Implementation**:
- Uses LangChain Expression Language (LCEL)
- Structured output with JSON parser
- Combines search and RAG results

**Analysis Pipeline**:
```python
prompt | llm | JsonOutputParser()
```

**Output Structure**:
```python
{
    "key_topics": List[str],
    "selected_article_urls": List[str],
    "reasoning": str,
    "sentiment": str
}
```

### 5. Summary Agent (`summary_agent.py`)

**Purpose**: Generate comprehensive summaries

**Features**:
- Markdown-formatted output
- Multiple summary types (brief/detailed)
- Contextual analysis integration

**Output Sections**:
- Executive Summary
- Key Points
- Analysis & Insights
- Context & Background
- Future Outlook
- Source Attribution

## Data Flow

```
1. User Query
   ↓
2. Search Agent → NewsArticle[]
   ↓
3. RAG Agent → Store new articles + Retrieve historical
   ↓
4. Analysis Agent → Select best articles + Analyze
   ↓
5. Summary Agent → Generate formatted summary
   ↓
6. Return to User
```

## Best Practices Implemented

### 1. Separation of Concerns
- Each agent has one responsibility
- Clear interfaces between components
- Easy to test and modify

### 2. Type Safety
```python
# Pydantic models everywhere
class NewsArticle(BaseModel):
    title: str
    url: str
    # ... with validation

class AgentState(BaseModel):
    user_query: str
    # ... with type hints
```

### 3. Error Handling
```python
try:
    result = agent.run(state)
except Exception as e:
    logger.error(f"Error: {e}")
    state.metadata["error"] = str(e)
    # Continue with degraded functionality
```

### 4. Logging
```python
# Structured logging throughout
logger.info(f"Processing query: {query}")
logger.debug(f"State: {state}")
logger.error(f"Error: {e}", exc_info=True)
```

### 5. Configuration Management
```python
# Environment-based config
llm = get_llm_openai()  # or get_llm_openrouter()
# Easy to swap implementations
```

### 6. State Management
```python
# Immutable state transitions
state = self.agent.run(state)
# Full audit trail in state.completed_agents
```

## Extensibility Points

### Adding New Agents

```python
# 1. Create new agent
class NewAgent:
    def run(self, state: AgentState) -> AgentState:
        # Your logic here
        state.completed_agents.append("new_agent")
        return state

# 2. Add to orchestrator
workflow.add_node("new", self._new_node)
workflow.add_edge("analysis", "new")
workflow.add_edge("new", "summary")
```

### Adding New Data Sources

```python
# In tools/agent_tools.py
@tool
def new_search_tool(query: str) -> str:
    """Search new source."""
    # Implementation
    return results
```

### Customizing Prompts

Each agent has its own prompt template that can be modified:

```python
# In analysis_agent.py
prompt = ChatPromptTemplate.from_messages([
    ("system", "Your custom system prompt"),
    ("human", "{query}\n{context}")
])
```

## Performance Considerations

### Vector Store Performance
- ChromaDB indexes are cached
- Embeddings are computed once
- Similarity search is O(log n)

### LLM Calls
- Streaming available (not yet implemented)
- Batching possible for multiple queries
- Caching recommended for production

### Memory Usage
- State is kept in memory during workflow
- Vector DB persists to disk
- Large articles are chunked

## Security Considerations

### API Keys
- Never committed to git
- Loaded from environment
- Separate keys for each service

### Input Validation
- Pydantic validates all inputs
- Type checking at runtime
- SQL injection not possible (vector DB)

### Output Sanitization
- Markdown output is safe
- URLs are validated
- No code execution in summaries

## Monitoring & Observability

### Logging Levels
- DEBUG: All state transitions
- INFO: Agent completions
- WARNING: Degraded functionality
- ERROR: Failures with stack traces

### Metrics to Track
- Query processing time
- Articles found/stored
- Agent success rates
- LLM token usage

## Future Architecture Improvements

1. **Caching Layer**: Redis for LLM responses
2. **Message Queue**: Celery for async processing
3. **API Gateway**: FastAPI for REST endpoints
4. **Monitoring**: Prometheus + Grafana
5. **A/B Testing**: Framework for prompt variations
6. **Streaming**: Real-time result streaming
