# Multi-Agent News System - REST API

A Flask-based REST API for querying the multi-agent news processing system with full LangSmith tracing integration.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required variables:
- `VALYU_API_KEY` - Your Valyu API key for news search
- `OPENROUTER_API_KEY` - Your OpenRouter API key (or `OPENAI_API_KEY`)
- `LANGCHAIN_API_KEY` - Your LangSmith API key (for tracing)
- `LANGCHAIN_TRACING_V2=true` - Enable LangSmith tracing

### 3. Start the API Server

```bash
python api.py
```

The server will start on `http://localhost:5000` by default.

### 4. Test the API

```bash
# In another terminal
python test_api.py
```

Or try the example usage:

```bash
python example_api_usage.py
```

## API Endpoints

### GET `/`
Get API information and status.

**Response:**
```json
{
  "service": "Multi-Agent News Processing System",
  "version": "1.0.0",
  "endpoints": {
    "POST /api/query": "Process a news query",
    "GET /api/stats": "Get RAG storage statistics",
    "GET /health": "Health check"
  },
  "langsmith": {
    "tracing_enabled": true,
    "project": "lock-in-hack-multi-agent"
  }
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "multi-agent-news-system"
}
```

### POST `/api/query`
Process a news query through the multi-agent system.

**Request Body:**
```json
{
  "query": "What are the latest developments in AI?"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "What are the latest developments in AI?",
    "summary": "Comprehensive summary of the news...",
    "analysis": "Analysis of the articles...",
    "search_results_count": 5,
    "rag_results_count": 3,
    "completed_agents": ["news_search", "rag", "analysis", "summary"],
    "metadata": {}
  },
  "langsmith_info": {
    "tracing_enabled": true,
    "project": "lock-in-hack-multi-agent",
    "dashboard_url": "https://smith.langchain.com/o/default/projects/p/lock-in-hack-multi-agent"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message here"
}
```

### GET `/api/stats`
Get RAG storage statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_documents": 100,
    "collection_name": "news_articles",
    "persist_directory": "/path/to/storage/chroma_db"
  }
}
```

## Usage Examples

### Python

```python
import requests

# Query the system
response = requests.post(
    "http://localhost:5000/api/query",
    json={"query": "What are the latest developments in AI?"}
)

result = response.json()
if result["success"]:
    print(result["data"]["summary"])
else:
    print(f"Error: {result['error']}")
```

### cURL

```bash
# Query endpoint
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in AI?"}'

# Stats endpoint
curl http://localhost:5000/api/stats

# Health check
curl http://localhost:5000/health
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:5000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'What are the latest developments in AI?'
  })
});

const result = await response.json();
if (result.success) {
  console.log(result.data.summary);
}
```

## LangSmith Tracing

All API requests are automatically traced in LangSmith when enabled. This includes:

- All LLM calls (GPT-4, etc.)
- Tool executions (Valyu search)
- Agent runs (search, RAG, analysis, summary)
- Complete workflow traces

### Viewing Traces

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Navigate to your project (e.g., "lock-in-hack-multi-agent")
3. View all traces with detailed information:
   - Input/output for each step
   - Latency and performance metrics
   - Token usage and costs
   - Error traces

### Trace Structure

Each API query creates a hierarchical trace:

```
process_query (main chain)
├── search_node
│   └── news_search_agent_run
│       └── news_search
│           └── valyu_search_tool
├── rag_node
│   └── rag_agent_run
│       ├── rag_store_articles
│       └── rag_retrieve_articles
├── analysis_node
│   └── analysis_agent_run
│       └── LLM call
└── summary_node
    └── summary_agent_run
        └── LLM call
```

## Configuration

Environment variables (in `.env`):

```bash
# API Configuration
FLASK_PORT=5000              # API server port
FLASK_DEBUG=false            # Enable debug mode (don't use in production)

# LLM Configuration
OPENROUTER_API_KEY=...       # OpenRouter API key
LLM_PROVIDER=openai          # Options: openai, bedrock

# Valyu Search
VALYU_API_KEY=...            # Valyu API key

# LangSmith Tracing
LANGCHAIN_TRACING_V2=true                      # Enable tracing
LANGCHAIN_API_KEY=...                          # LangSmith API key
LANGCHAIN_PROJECT=lock-in-hack-multi-agent     # Project name
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Logging
LOG_LEVEL=INFO               # Options: DEBUG, INFO, WARNING, ERROR
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request (e.g., missing query)
- `500 Internal Server Error` - Server error during processing

All errors include a descriptive message:

```json
{
  "success": false,
  "error": "Missing 'query' field in request body"
}
```

## Performance Considerations

- **First request** may take longer as the system initializes
- **Subsequent requests** use the same orchestrator instance (faster)
- **Typical query time**: 10-30 seconds depending on:
  - News search API response time
  - Number of articles to process
  - LLM response time
  - RAG retrieval complexity

## Development

### Running in Debug Mode

```bash
# In .env, set:
FLASK_DEBUG=true

# Then run:
python api.py
```

Debug mode provides:
- Auto-reload on code changes
- Detailed error traces
- Interactive debugger in browser

### Testing

Run the test suite:

```bash
python test_api.py
```

This tests all endpoints and verifies:
- Health check
- Stats endpoint
- Query processing
- Error handling

### Custom Queries

You can modify `example_api_usage.py` to test custom queries:

```python
queries = [
    "Your custom query here",
    "Another query",
]
```

## Deployment

### Production Considerations

1. **Use a production WSGI server** (not Flask's dev server):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 api:app
   ```

2. **Set `FLASK_DEBUG=false`** in production

3. **Use environment-specific .env files**

4. **Enable HTTPS** with a reverse proxy (nginx, Apache)

5. **Add rate limiting** to prevent abuse

6. **Monitor with LangSmith** for production issues

### Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_PORT=5000
EXPOSE 5000

CMD ["python", "api.py"]
```

Build and run:

```bash
docker build -t multi-agent-news-api .
docker run -p 5000:5000 --env-file .env multi-agent-news-api
```

## Troubleshooting

### API won't start

1. Check if port 5000 is available:
   ```bash
   lsof -i :5000
   ```

2. Use a different port:
   ```bash
   FLASK_PORT=8000 python api.py
   ```

### Queries failing

1. Check environment variables are set:
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('VALYU_API_KEY:', os.getenv('VALYU_API_KEY')[:10])"
   ```

2. Check API server logs for detailed errors

3. Verify LangSmith traces for specific failure points

### Tracing not working

See [LANGSMITH_SETUP.md](LANGSMITH_SETUP.md) for detailed troubleshooting.

## Support

- Check the main [README.md](README.md) for general information
- See [LANGSMITH_SETUP.md](LANGSMITH_SETUP.md) for tracing setup
- Open an issue for bugs or feature requests
