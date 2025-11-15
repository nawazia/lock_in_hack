# LangSmith Trace Visualizer

Interactive graph visualization for LangSmith traces using React Flow. This provides a visual representation of your multi-agent system's execution flow with detailed inspection capabilities.

## Overview

This visualization tool transforms LangSmith trace data into an interactive graph where:
- **Nodes** represent individual runs (LLM calls, tool executions, chains, etc.)
- **Edges** show parent-child relationships between runs
- **Colors** indicate run types (Blue=LLM, Green=Tool, Purple=Chain, Orange=Retriever)
- **Size** reflects latency and token usage
- **Click** any node to view complete LangSmith data in a sidebar

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Port 3000)               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ TraceVisualizer│→│  CustomNode  │  │ NodeSidebar  │      │
│  │  (Main UI)    │  │  (Renderer)  │  │  (Details)   │      │
│  └──────┬────────┘  └──────────────┘  └──────────────┘      │
│         │                                                     │
│         ├─→ ReactFlow (Graph rendering)                      │
│         ├─→ traceProcessor.js (Data transformation)          │
│         └─→ api.js (Backend communication)                   │
│                          │                                    │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP API
┌──────────────────────────┼──────────────────────────────────┐
│                  Flask Backend (Port 5000)                    │
│                          │                                    │
│  ┌───────────────────────▼───────────────────────┐           │
│  │  GET /api/traces                              │           │
│  │  GET /api/traces/{run_id}                     │           │
│  │  GET /api/traces/latest                       │           │
│  └───────────────────┬───────────────────────────┘           │
│                      │                                        │
│              ┌───────▼───────┐                                │
│              │ LangSmith     │                                │
│              │ Client        │                                │
│              └───────┬───────┘                                │
└──────────────────────┼──────────────────────────────────────┘
                       │
              ┌────────▼─────────┐
              │  LangSmith API   │
              │ (smith.langchain │
              │     .com)        │
              └──────────────────┘
```

## Features

### 1. Interactive Graph Visualization
- **Hierarchical Layout**: Parent-child relationships clearly displayed
- **Zoom & Pan**: Navigate large traces easily
- **Minimap**: Overview of entire graph
- **Smooth Animations**: Animated edges for LLM calls

### 2. Color-Coded Node Types
- 🤖 **Blue**: LLM calls (GPT-4, etc.)
- 🔧 **Green**: Tool executions (Valyu search, etc.)
- ⛓️ **Purple**: Chain calls (orchestration)
- 🔍 **Orange**: Retriever operations (RAG)
- ❌ **Red Border**: Errors

### 3. Node Sizing
Nodes are dynamically sized based on:
- **Latency**: Longer operations = larger nodes
- **Token Count**: More tokens = wider nodes

### 4. Detailed Sidebar
Click any node to view:
- Start/end time & latency
- Token usage (prompt, completion, total)
- Full inputs & outputs
- Error messages
- Tags & metadata
- Feedback statistics

### 5. Statistics Panel
Top panel shows aggregate metrics:
- Total runs
- LLM/Tool/Chain call counts
- Total tokens used
- Total execution time
- Error count

### 6. Trace Selection
- Browse all available traces
- Jump to specific runs
- Auto-load latest trace

## How It Works

### Data Flow

1. **Backend Fetches Traces**
   - Flask API calls LangSmith Client
   - Retrieves run data from LangSmith API
   - Converts to JSON format

2. **Frontend Processes Data**
   - `traceProcessor.js` transforms flat run list into hierarchical tree
   - Calculates node positions, sizes, and colors
   - Generates React Flow nodes and edges

3. **Graph Rendering**
   - React Flow renders the graph
   - CustomNode components display run info
   - User clicks node → sidebar shows details

4. **User Interaction**
   - Click nodes to inspect
   - Zoom/pan to navigate
   - Select different traces from dropdown

### Key Components

#### `TraceVisualizer.jsx` (Main Component)
- Manages graph state
- Fetches trace data from backend
- Handles user interactions
- Coordinates all child components

**State:**
```javascript
- nodes: React Flow nodes
- edges: React Flow edges
- selectedNode: Currently selected node
- traceStats: Aggregate statistics
- availableTraces: List of traces
```

#### `CustomNode.jsx` (Node Renderer)
- Renders individual nodes in the graph
- Shows icon, name, type, metrics
- Highlights on selection
- Color-coded by type

**Props:**
```javascript
data: {
  name, runType, status,
  latencyFormatted, totalTokens,
  error, color, size
}
```

#### `NodeSidebar.jsx` (Details Panel)
- Displays complete run information
- Fixed position on right side
- Scrollable content
- JSON formatting for inputs/outputs

**Sections:**
- Basic info (name, type, status, times)
- Token usage (for LLM calls)
- Errors (if any)
- Tags
- Metadata
- Inputs (formatted JSON)
- Outputs (formatted JSON)
- Feedback stats

#### `StatsPanel.jsx` (Metrics Display)
- Shows aggregate statistics
- Color-coded stat cards
- Always visible at top

#### `traceProcessor.js` (Data Transformation)
**Functions:**
- `processTraceData()`: Main entry point
- `buildTraceTree()`: Creates parent-child relationships
- `treeToFlowGraph()`: Converts tree to React Flow format
- `calculateNodeSize()`: Determines node dimensions
- `getNodeColor()`: Assigns colors by type
- `getTraceStats()`: Calculates aggregate metrics

**Processing Steps:**
1. Build run map (id → run)
2. Create tree structure (parent → children)
3. Calculate layout positions
4. Generate React Flow nodes with styling
5. Create edges between parent-child pairs

#### `api.js` (Backend Client)
**Functions:**
- `fetchTraceRuns()`: Get list of available traces
- `fetchTraceDetails(runId)`: Get full trace data
- `fetchLatestTrace()`: Get most recent trace

## Setup & Installation

### Prerequisites
- Node.js 16+ and npm
- Python 3.8+ with Flask API running
- LangSmith account with API key

### Installation

1. **Install Dependencies**
   ```bash
   cd graph-ui
   npm install
   ```

2. **Configure Environment**

   The frontend connects to Flask API at `http://localhost:5000`.
   Ensure your Flask API has:
   - LangSmith tracing enabled
   - `LANGCHAIN_TRACING_V2=true`
   - `LANGCHAIN_API_KEY=your_key`

3. **Start Development Server**
   ```bash
   npm run dev
   ```

   Opens at `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## Usage

### 1. Generate Trace Data

First, run a query through the Flask API to generate traces:

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest AI developments?"}'
```

### 2. View Visualization

Open `http://localhost:3000` in your browser.

The latest trace loads automatically, or:
- Use the dropdown to select a specific trace
- Click "Refresh" to reload data

### 3. Explore the Graph

- **Pan**: Click and drag background
- **Zoom**: Mouse wheel or controls
- **Select Node**: Click any node
- **View Details**: Sidebar appears on right
- **Close Sidebar**: Click X or click background

### 4. Understand the Visualization

**Example Trace Flow:**
```
process_query (Purple chain)
├─→ search_node (Purple chain)
│   └─→ news_search_agent_run (Purple chain)
│       └─→ news_search (Purple chain)
│           └─→ valyu_search_tool (Green tool)
├─→ rag_node (Purple chain)
│   └─→ rag_agent_run (Purple chain)
│       ├─→ rag_store_articles (Purple chain)
│       └─→ rag_retrieve_articles (Purple chain)
├─→ analysis_node (Purple chain)
│   └─→ analysis_agent_run (Purple chain)
│       └─→ LLM call (Blue LLM)
└─→ summary_node (Purple chain)
    └─→ summary_agent_run (Purple chain)
        └─→ LLM call (Blue LLM)
```

**Node Information:**
- Large blue nodes = LLM calls (expensive, token-heavy)
- Small green nodes = Tool calls (fast, no tokens)
- Purple chains = Orchestration/workflow steps
- Red borders = Errors occurred

## API Endpoints Used

The frontend calls these Flask API endpoints:

### `GET /api/traces`
Returns list of available traces.

**Response:**
```json
{
  "success": true,
  "traces": [
    {
      "id": "run-uuid-here",
      "name": "process_query",
      "start_time": "2025-01-15T10:30:00",
      "end_time": "2025-01-15T10:30:05",
      "run_type": "chain",
      "status": "success"
    }
  ]
}
```

### `GET /api/traces/{run_id}`
Returns detailed trace data for specific run.

**Response:**
```json
{
  "success": true,
  "trace": {
    "run_id": "...",
    "runs": [
      {
        "id": "...",
        "name": "...",
        "run_type": "llm|tool|chain",
        "start_time": "...",
        "end_time": "...",
        "inputs": {},
        "outputs": {},
        "error": null,
        "tags": [],
        "total_tokens": 1234,
        "prompt_tokens": 500,
        "completion_tokens": 734,
        "parent_run_id": null,
        "child_run_ids": ["..."]
      }
    ]
  }
}
```

### `GET /api/traces/latest`
Returns most recent trace (auto-loads on page load).

## Customization

### Change Color Scheme

Edit `src/utils/traceProcessor.js`:

```javascript
const RUN_TYPE_COLORS = {
  llm: '#3B82F6',      // Change LLM color
  tool: '#10B981',     // Change tool color
  chain: '#8B5CF6',    // Change chain color
  // ...
};
```

### Adjust Node Sizing

Edit `calculateNodeSize()` in `traceProcessor.js`:

```javascript
const baseSize = 180;           // Base width
const latencyFactor = ...;      // Latency multiplier
const tokenFactor = ...;        // Token multiplier
```

### Modify Layout

Edit `treeToFlowGraph()` in `traceProcessor.js`:

```javascript
const levelSpacing = 200;  // Horizontal spacing
const nodeSpacing = 50;    // Vertical spacing
```

## Troubleshooting

### No Traces Showing

**Check:**
1. Flask API is running (`http://localhost:5000`)
2. LangSmith tracing is enabled in `.env`
3. You've run at least one query through the API
4. Browser console for errors (F12)

**Fix:**
```bash
# Terminal 1: Start Flask API
cd /path/to/project
python api.py

# Terminal 2: Run a query
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Terminal 3: Start frontend
cd graph-ui
npm run dev
```

### "LangSmith client not initialized" Error

The Flask backend couldn't connect to LangSmith.

**Check `.env`:**
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_actual_key_here
LANGCHAIN_PROJECT=lock-in-hack-multi-agent
```

**Verify:**
```bash
python -c "from langsmith import Client; c = Client(); print('Connected!')"
```

### Nodes Not Rendering Correctly

**Clear browser cache:**
- Chrome: Ctrl+Shift+Del
- Refresh: Ctrl+R (or Cmd+R on Mac)

**Check browser console:**
- Press F12 → Console tab
- Look for JavaScript errors

### Graph Too Large/Small

**Adjust zoom:**
- Use mouse wheel
- Use zoom controls (bottom left)
- Click "fit view" button

**Change initial layout:**
Edit `TraceVisualizer.jsx`:
```javascript
<ReactFlow
  fitView
  defaultZoom={0.8}  // Adjust zoom level
  minZoom={0.1}
  maxZoom={2}
/>
```

## Performance

### Handling Large Traces

The visualization handles traces with:
- ✅ Up to 100 nodes: Smooth
- ⚠️ 100-500 nodes: May slow down
- ❌ 500+ nodes: Consider filtering

**Optimization for large traces:**
1. Filter by run type in backend
2. Limit depth of recursion
3. Paginate trace results

### Memory Usage

Each node stores:
- Full input/output data
- Metadata
- Styling information

For very large traces, consider:
- Lazy-loading node details
- Virtualizing sidebar content
- Limiting displayed nodes

## File Structure

```
graph-ui/
├── package.json              # Dependencies
├── vite.config.js           # Build configuration
├── index.html               # HTML entry point
├── README.md                # This file
│
├── src/
│   ├── main.jsx             # React entry point
│   ├── App.jsx              # Root component
│   ├── index.css            # Global styles
│   │
│   ├── components/
│   │   ├── TraceVisualizer.jsx   # Main UI component
│   │   ├── CustomNode.jsx        # Node renderer
│   │   ├── NodeSidebar.jsx       # Details panel
│   │   └── StatsPanel.jsx        # Statistics display
│   │
│   ├── services/
│   │   └── api.js                # Backend API client
│   │
│   └── utils/
│       └── traceProcessor.js     # Data transformation
│
└── public/
    └── (static assets)
```

## Technology Stack

- **React 18**: UI framework
- **React Flow 11**: Graph visualization library
- **Vite**: Build tool & dev server
- **Axios**: HTTP client
- **Lucide React**: Icon library

## Future Enhancements

Potential improvements:
- [ ] Real-time trace updates (WebSocket)
- [ ] Search/filter nodes by name/type
- [ ] Collapse/expand subtrees
- [ ] Export graph as image/PDF
- [ ] Compare multiple traces side-by-side
- [ ] Time-series view of traces
- [ ] Cost breakdown visualization
- [ ] Custom node layouts (tree, force-directed, etc.)
- [ ] Dark mode theme

## Contributing

To extend the visualization:

1. **Add new node types**: Edit `RUN_TYPE_COLORS` in `traceProcessor.js`
2. **Add metrics**: Extend `extractMetrics()` function
3. **Customize sidebar**: Edit `NodeSidebar.jsx` sections
4. **Add filters**: Implement in `TraceVisualizer.jsx`

## Support

For issues:
1. Check browser console (F12)
2. Check Flask API logs
3. Verify LangSmith connection
4. Review this README

---

**Built with ❤️ for visualizing multi-agent LLM systems**
