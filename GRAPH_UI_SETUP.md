# LangSmith Trace Graph Visualization - Setup Complete ✅

An interactive React Flow visualization for LangSmith traces has been added to your multi-agent system.

## What Was Built

A complete React-based graph visualization tool that:
- ✅ Fetches trace data from LangSmith via Flask API
- ✅ Renders interactive hierarchical graphs with React Flow
- ✅ Color-codes nodes by type (LLM=Blue, Tool=Green, Chain=Purple)
- ✅ Sizes nodes based on latency and token usage
- ✅ Shows detailed trace data in a sidebar when clicking nodes
- ✅ Displays aggregate statistics (tokens, latency, run counts)
- ✅ Allows browsing and selecting different traces

## Quick Start

### 1. Install Frontend Dependencies

```bash
cd graph-ui
npm install
```

### 2. Start Flask API (if not running)

```bash
# From project root
python api.py
```

### 3. Start Visualization

```bash
# From graph-ui directory
npm run dev
```

Opens at: **http://localhost:3000**

### 4. Generate a Trace

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest AI developments?"}'
```

Refresh the visualization to see your trace!

## File Structure

```
graph-ui/
├── README.md                    # Complete documentation
├── QUICKSTART.md                # Quick start guide
├── package.json                 # Dependencies
├── vite.config.js              # Vite config
├── start.sh                     # Startup script
│
└── src/
    ├── components/
    │   ├── TraceVisualizer.jsx # Main UI
    │   ├── CustomNode.jsx      # Node renderer
    │   ├── NodeSidebar.jsx     # Details panel
    │   └── StatsPanel.jsx      # Stats display
    │
    ├── services/
    │   └── api.js              # API client
    │
    └── utils/
        └── traceProcessor.js   # Data processing
```

## Features

### Interactive Graph
- **Hierarchical Layout**: Shows parent-child relationships
- **Zoom & Pan**: Navigate large traces
- **Minimap**: Overview of entire graph
- **Animated Edges**: For LLM calls

### Color Coding
- 🤖 **Blue**: LLM calls
- 🔧 **Green**: Tool executions
- ⛓️ **Purple**: Chains/orchestration
- 🔍 **Orange**: Retrievers
- ❌ **Red Border**: Errors

### Node Information
Each node displays:
- Name and type
- Latency
- Token count (for LLMs)
- Status indicator

### Detailed Sidebar
Click any node to see:
- Start/end times
- Full inputs & outputs
- Token usage breakdown
- Error messages
- Tags & metadata
- Feedback statistics

### Statistics Panel
Top panel shows:
- Total runs
- LLM/Tool/Chain counts
- Total tokens
- Total execution time
- Error count

## Backend Integration

Three new API endpoints were added to `api.py`:

### `GET /api/traces`
List all available traces

### `GET /api/traces/{run_id}`
Get detailed trace data for a specific run

### `GET /api/traces/latest`
Get the most recent trace (auto-loads on page load)

All endpoints use the LangSmith Client to fetch data.

## How It Works

```
1. User Query → Flask API → LangSmith (trace recorded)
                    ↓
2. Frontend calls /api/traces/latest
                    ↓
3. Flask fetches trace from LangSmith API
                    ↓
4. Frontend processes data:
   - Builds parent-child tree
   - Calculates positions & sizes
   - Assigns colors
   - Creates React Flow nodes/edges
                    ↓
5. Graph renders interactively
                    ↓
6. User clicks node → Sidebar shows details
```

## Data Flow

```
LangSmith API
      ↓
Flask Backend (api.py)
  - LangSmithClient.list_runs()
  - LangSmithClient.read_run()
      ↓
JSON Response
      ↓
React Frontend (api.js)
      ↓
traceProcessor.js
  - buildTraceTree()
  - treeToFlowGraph()
  - calculateNodeSize()
  - getNodeColor()
      ↓
React Flow Nodes + Edges
      ↓
TraceVisualizer renders
      ↓
User interacts
```

## Example Trace Visualization

When you run a query, you'll see:

```
process_query (Purple chain at top)
    ├─→ search_node
    │       └─→ news_search_agent_run
    │               └─→ news_search
    │                       └─→ valyu_search_tool (Green)
    │
    ├─→ rag_node
    │       └─→ rag_agent_run
    │               ├─→ rag_store_articles
    │               └─→ rag_retrieve_articles
    │
    ├─→ analysis_node
    │       └─→ analysis_agent_run
    │               └─→ LLM call (Blue, large)
    │
    └─→ summary_node
            └─→ summary_agent_run
                    └─→ LLM call (Blue, large)
```

Larger blue nodes indicate expensive LLM calls with high token counts.

## Customization

All documented in [graph-ui/README.md](graph-ui/README.md):
- Change colors
- Adjust node sizing
- Modify layout spacing
- Add new metrics
- Customize sidebar sections

## Tech Stack

- **React 18**: UI framework
- **React Flow 11**: Graph visualization
- **Vite**: Build tool
- **Axios**: HTTP client
- **Lucide React**: Icons

## Troubleshooting

### No traces showing?
1. Check Flask API is running: `curl http://localhost:5000/health`
2. Verify LangSmith config in `.env`
3. Run a test query (see Quick Start above)
4. Check browser console (F12) for errors

### "LangSmith client not initialized"?
Check `.env` has:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key_here
```

### Graph not rendering?
1. Clear browser cache
2. Check console for errors
3. Verify API responses: `curl http://localhost:5000/api/traces/latest`

## Documentation

- **[graph-ui/README.md](graph-ui/README.md)**: Complete technical documentation
- **[graph-ui/QUICKSTART.md](graph-ui/QUICKSTART.md)**: Quick start guide
- **This file**: Integration overview

## Next Steps

1. **Install**: `cd graph-ui && npm install`
2. **Start**: `npm run dev`
3. **Explore**: Click nodes, zoom, pan
4. **Customize**: Edit colors, sizing, layout
5. **Extend**: Add new features (see README)

---

**Visualization ready!** 🎉

Open http://localhost:3000 after starting the dev server.
