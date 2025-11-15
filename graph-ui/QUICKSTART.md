# Quick Start Guide

Get the LangSmith Trace Visualizer running in 3 steps.

## Prerequisites

- Node.js 16+ installed
- Flask API running with LangSmith tracing enabled
- At least one trace generated

## Step 1: Install Dependencies

```bash
cd graph-ui
npm install
```

## Step 2: Ensure Flask API is Running

In a separate terminal:

```bash
# From project root
python api.py
```

Verify it's running:
```bash
curl http://localhost:5000/health
# Should return: {"status":"healthy","service":"multi-agent-news-system"}
```

## Step 3: Start the Visualization

```bash
# Option 1: Use the startup script
./start.sh

# Option 2: Run directly
npm run dev
```

Opens at: **http://localhost:3000**

## Generate Your First Trace

If you don't have any traces yet:

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in AI?"}'
```

Then refresh the visualization!

## What You Should See

1. **Header**: Title and refresh button
2. **Stats Panel**: Aggregate metrics (runs, tokens, latency)
3. **Graph**: Interactive node graph
   - Purple nodes = Chains
   - Blue nodes = LLM calls
   - Green nodes = Tools
4. **Legend**: Bottom left corner

## Basic Controls

- **Pan**: Click and drag
- **Zoom**: Mouse wheel
- **Select Node**: Click any node
- **View Details**: Sidebar appears with full data
- **Close Sidebar**: Click X or background

## Troubleshooting

### "No traces available"
→ Run a query through the Flask API first (see above)

### "Cannot connect to API"
→ Ensure Flask is running on port 5000

### "LangSmith client not initialized"
→ Check `.env` has `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`

## Next Steps

See [README.md](README.md) for:
- Complete feature documentation
- Architecture details
- Customization options
- Advanced usage
