# Multi-Agent News Processing System

A sophisticated multi-agent system built with LangChain and LangGraph that intelligently processes news queries using an orchestrated workflow of specialized agents.

## 🏗️ Architecture

The system consists of 5 main components orchestrated via LangGraph:

```
User Query
    ↓
┌─────────────────────────────────────────┐
│      Orchestrator Agent                 │
│      (LangGraph Workflow)               │
└─────────────────────────────────────────┘
    ↓           ↓           ↓           ↓
┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
│Search│ → │ RAG  │ → │Analyze│ → │Summary│
│Agent │   │Agent │   │ Agent │   │ Agent │
└──────┘   └──────┘   └──────┘   └──────┘
```

### Agent Responsibilities

1. **News Search Agent** (`news_search_agent.py`)
   - Searches for news using the Valyu API
   - Structures results into `NewsArticle` objects
   - Uses tool-calling to interact with external APIs

2. **RAG Agent** (`rag_agent.py`)
   - Stores news articles in ChromaDB vector store
   - Retrieves relevant historical articles
   - Manages embeddings and similarity search
   - Persists data for long-term memory

3. **Analysis Agent** (`analysis_agent.py`)
   - Analyzes both new and historical articles
   - Identifies key topics and themes
   - Selects most relevant articles
   - Assesses sentiment and credibility

4. **Summary Agent** (`summary_agent.py`)
   - Generates comprehensive summaries
   - Structures output with markdown
   - Provides context and implications
   - Creates both detailed and brief summaries

5. **Orchestrator Agent** (`orchestrator.py`)
   - Coordinates all agents using LangGraph
   - Manages state flow between agents
   - Handles errors gracefully
   - Provides workflow visualization

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- OpenAI API key (for LLM and embeddings)
- Valyu API key (for news search)

### Installation

1. Clone the repository and navigate to the project:
```bash
cd lock_in_hack
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```
OPENAI_API_KEY=sk-...
VALYU_API_KEY=...
```

### Usage

#### Basic Usage

Run the default example:
```bash
python run_agent.py
```

#### Custom Queries

Edit `run_agent.py` to add your own queries:
```python
queries = [
    "What are the latest developments in AI?",
    "Tell me about recent climate change news",
]
```

#### Programmatic Usage

```python
from agents.orchestrator import build_agent

# Initialize the orchestrator
orchestrator = build_agent()

# Process a query
result = orchestrator.process_query("What's happening with cryptocurrency?")

# Access results
print(result["summary"])
print(result["analysis"])
```

#### RAG Storage Management

```python
# Get RAG statistics
stats = orchestrator.get_rag_stats()
print(f"Total articles stored: {stats['total_documents']}")

# Direct RAG access
from agents.rag_agent import RAGAgent

rag = RAGAgent()
articles = rag.retrieve_articles("AI news", k=5)
```

## 📁 Project Structure

```
lock_in_hack/
├── agents/
│   ├── __init__.py
│   ├── news_search_agent.py    # News search functionality
│   ├── rag_agent.py             # Vector store management
│   ├── analysis_agent.py        # Article analysis
│   ├── summary_agent.py         # Summary generation
│   └── orchestrator.py          # LangGraph orchestration
├── models/
│   ├── __init__.py
│   └── schemas.py               # Pydantic data models
├── tools/
│   └── agent_tools.py           # LangChain tools (Valyu search)
├── config/
│   ├── llm_setup.py             # LLM configuration
│   └── BedrockProxyLLM.py       # Custom Bedrock LLM
├── utils/
│   ├── __init__.py
│   └── logger.py                # Logging configuration
├── storage/
│   └── chroma_db/               # Vector store persistence
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── run_agent.py                 # Main entry point
└── README.md                    # This file
```

## 🎯 Key Features

### Best Practices Implemented

1. **Modular Architecture**
   - Separation of concerns
   - Each agent has a single responsibility
   - Easy to extend and modify

2. **Type Safety**
   - Pydantic models for data validation
   - Type hints throughout
   - Runtime validation

3. **Error Handling**
   - Graceful degradation
   - Comprehensive logging
   - Error tracking in state

4. **State Management**
   - Centralized `AgentState` model
   - Immutable state transitions
   - Full audit trail

5. **Configuration Management**
   - Environment-based configuration
   - Multiple LLM provider support
   - Flexible deployment options

6. **Persistent Storage**
   - ChromaDB for vector storage
   - Automatic persistence
   - Efficient similarity search

7. **LangGraph Orchestration**
   - Clear workflow definition
   - Easy to visualize
   - Deterministic execution

## 🔧 Configuration

### LLM Providers

The system supports multiple LLM providers:

**OpenAI** (default):
```python
from config.llm_setup import get_llm_openai
llm = get_llm_openai()
```

**OpenRouter** (for Claude):
```python
from config.llm_setup import get_llm_openrouter
llm = get_llm_openrouter()
```

**AWS Bedrock**:
```python
from config.BedrockProxyLLM import BedrockProxyLLM
llm = BedrockProxyLLM()
```

### Vector Store Options

Change the vector store by modifying `RAGAgent`:
```python
# Use FAISS instead of ChromaDB
from langchain_community.vectorstores import FAISS

# In rag_agent.py, replace Chroma with FAISS
```

## 📊 Data Models

### NewsArticle
```python
class NewsArticle(BaseModel):
    title: str
    url: str
    content: str
    source: str = "valyu"
    timestamp: datetime
    query: Optional[str]
    relevance_score: Optional[float]
```

### AgentState
```python
class AgentState(BaseModel):
    user_query: str
    search_results: List[NewsArticle]
    rag_results: List[NewsArticle]
    analysis: Optional[str]
    summary: Optional[str]
    next_agent: Optional[str]
    completed_agents: List[str]
    metadata: Dict[str, Any]
```

## 🚧 Future Enhancements

- [ ] Add caching for LLM responses
- [ ] Implement streaming for real-time results
- [ ] Add web UI with Streamlit/Gradio
- [ ] Support for more news sources
- [ ] Multi-language support
- [ ] Performance metrics dashboard

## 🙏 Acknowledgments

- LangChain for the agent framework
- LangGraph for orchestration
- Valyu for news search API
- OpenAI for LLM capabilities