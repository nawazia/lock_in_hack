# LangSmith Trace Graph Visualization - Implementation Details

## Overview

This document explains how the LangSmith trace visualization was implemented and how all the pieces work together.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Browser (localhost:3000)                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              TraceVisualizer Component                      │ │
│  │                                                              │ │
│  │  State:                                                      │ │
│  │  - nodes: React Flow nodes (visual elements)                │ │
│  │  - edges: React Flow edges (connections)                    │ │
│  │  - selectedNode: Currently clicked node                     │ │
│  │  - traceStats: Aggregate metrics                            │ │
│  │                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │ StatsPanel   │  │  ReactFlow   │  │ NodeSidebar  │      │ │
│  │  │ (Top bar)    │  │  (Graph)     │  │ (Right side) │      │ │
│  │  └──────────────┘  └──────┬───────┘  └──────────────┘      │ │
│  │                           │                                  │ │
│  │                    ┌──────▼───────┐                          │ │
│  │                    │ CustomNode   │ (repeated for each node) │ │
│  │                    │ Components   │                          │ │
│  │                    └──────────────┘                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                      ┌───────▼────────┐                          │
│                      │   api.js       │                          │
│                      │ (HTTP Client)  │                          │
│                      └───────┬────────┘                          │
└──────────────────────────────┼──────────────────────────────────┘
                               │ HTTP GET /api/traces/*
┌──────────────────────────────┼──────────────────────────────────┐
│              Flask Backend (localhost:5000)                      │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │                 API Endpoints (api.py)                      │ │
│  │                                                              │ │
│  │  GET /api/traces           → List all traces                │ │
│  │  GET /api/traces/{id}      → Get trace details              │ │
│  │  GET /api/traces/latest    → Get most recent                │ │
│  └───────────────────────┬──────────────────────────────────── │ │
│                          │                                      │ │
│              ┌───────────▼────────────┐                         │ │
│              │  LangSmith Client      │                         │ │
│              │  - list_runs()         │                         │ │
│              │  - read_run()          │                         │ │
│              └───────────┬────────────┘                         │ │
└──────────────────────────┼──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────┼──────────────────────────────────────┐
│                 LangSmith API (smith.langchain.com)              │
│                                                                  │
│  Stores all trace data from your multi-agent runs               │
└──────────────────────────────────────────────────────────────────┘
```

## Data Transformation Pipeline

### Step 1: Fetch from LangSmith

**Flask Backend** (`api.py`):
```python
def get_trace_details(run_id):
    # Recursively fetch run and all children
    def fetch_run_tree(run_id):
        run = langsmith_client.read_run(run_id)
        # Convert to dict with all fields
        run_dict = {
            "id": str(run.id),
            "name": run.name,
            "run_type": run.run_type,
            "start_time": run.start_time.isoformat(),
            # ... all other fields
            "parent_run_id": str(run.parent_run_id),
            "child_run_ids": [str(cid) for cid in run.child_run_ids]
        }
        runs_data.append(run_dict)

        # Fetch children recursively
        for child_id in run.child_run_ids:
            fetch_run_tree(child_id)

    fetch_run_tree(run_id)
    return {"runs": runs_data}
```

**Output**: Flat list of runs with parent/child IDs

### Step 2: Transform to Tree

**Frontend** (`traceProcessor.js` → `buildTraceTree()`):
```javascript
function buildTraceTree(runs) {
    const runMap = new Map();
    const rootRuns = [];

    // First pass: create map
    runs.forEach(run => {
        runMap.set(run.id, { ...run, children: [] });
    });

    // Second pass: build relationships
    runs.forEach(run => {
        const node = runMap.get(run.id);
        if (run.parent_run_id) {
            const parent = runMap.get(run.parent_run_id);
            parent.children.push(node);
        } else {
            rootRuns.push(node);
        }
    });

    return { runMap, rootRuns };
}
```

**Output**: Hierarchical tree structure

### Step 3: Convert to React Flow Format

**Frontend** (`traceProcessor.js` → `treeToFlowGraph()`):
```javascript
function treeToFlowGraph(rootRuns) {
    const nodes = [];
    const edges = [];
    let yOffset = 0;

    function processNode(node, level, parentId) {
        const size = calculateNodeSize(node);
        const color = getNodeColor(node);

        // Create React Flow node
        nodes.push({
            id: node.id,
            type: 'custom',
            position: {
                x: level * 200,  // Horizontal spacing
                y: yOffset        // Vertical position
            },
            data: { ...node, color, size },
            style: {
                width: size.width,
                height: size.height,
                backgroundColor: color,
                // ... styling
            }
        });

        // Create edge from parent
        if (parentId) {
            edges.push({
                id: `${parentId}-${node.id}`,
                source: parentId,
                target: node.id,
                type: 'smoothstep',
                animated: node.runType === 'llm'
            });
        }

        yOffset += size.height + 50;

        // Process children
        node.children.forEach(child => {
            processNode(child, level + 1, node.id);
        });
    }

    rootRuns.forEach(root => processNode(root, 0, null));

    return { nodes, edges };
}
```

**Output**: React Flow-compatible nodes and edges

### Step 4: Calculate Visual Properties

**Node Size** (`calculateNodeSize()`):
```javascript
function calculateNodeSize(run) {
    const baseSize = 180;

    // Calculate latency in seconds
    const latencyMs = new Date(run.end_time) - new Date(run.start_time);
    const latencySeconds = latencyMs / 1000;
    const latencyFactor = Math.min(latencySeconds, 10); // Cap at 10s

    // Calculate token factor
    const totalTokens = run.total_tokens || 0;
    const tokenFactor = Math.min(totalTokens / 1000, 10); // Cap at 10k

    // Size formula
    const width = baseSize + (latencyFactor * 5) + (tokenFactor * 3);
    const height = 120 + (latencyFactor * 2);

    return { width: Math.round(width), height: Math.round(height) };
}
```

**Node Color** (`getNodeColor()`):
```javascript
const RUN_TYPE_COLORS = {
    llm: '#3B82F6',      // Blue
    tool: '#10B981',     // Green
    chain: '#8B5CF6',    // Purple
    retriever: '#F59E0B' // Orange
};

function getNodeColor(run) {
    if (run.error) return '#EF4444'; // Red for errors
    return RUN_TYPE_COLORS[run.run_type] || '#6B7280';
}
```

## Component Breakdown

### TraceVisualizer.jsx

**Purpose**: Main container component

**Responsibilities**:
- Fetch trace data from API
- Manage graph state (nodes, edges)
- Handle user interactions
- Coordinate child components

**Key Functions**:
```javascript
loadTrace(traceId) {
    // 1. Fetch from API
    const response = await fetchTraceDetails(traceId);

    // 2. Process data
    const { nodes, edges } = processTraceData(response.trace);

    // 3. Update state
    setNodes(nodes);
    setEdges(edges);
    setTraceStats(getTraceStats(response.trace));
}

onNodeClick(event, node) {
    // Show sidebar with node details
    setSelectedNode(node);
}
```

### CustomNode.jsx

**Purpose**: Render individual nodes

**Props Received**:
```javascript
{
    data: {
        name: "process_query",
        runType: "chain",
        status: "success",
        latencyFormatted: "5.2s",
        totalTokens: 3521,
        error: null,
        color: "#8B5CF6",
        size: { width: 180, height: 120 }
    }
}
```

**Renders**:
- Icon (based on run type)
- Name (truncated if long)
- Status indicator (✅ ❌ ⏳)
- Metrics (latency, tokens)
- Error badge (if error exists)

### NodeSidebar.jsx

**Purpose**: Display detailed information

**Sections**:
1. **Basic Info**: Name, type, status, times, latency
2. **Token Usage**: Total, prompt, completion (for LLMs)
3. **Error**: Full error message (if error)
4. **Tags**: Tag chips
5. **Metadata**: JSON object
6. **Inputs**: Formatted JSON
7. **Outputs**: Formatted JSON
8. **Feedback Stats**: User feedback data

**Formatting**:
```javascript
formatJson(obj) {
    if (typeof obj === 'string') return obj;
    return JSON.stringify(obj, null, 2);
}
```

### StatsPanel.jsx

**Purpose**: Show aggregate metrics

**Metrics Calculated**:
```javascript
{
    totalRuns: runs.length,
    llmCalls: runs.filter(r => r.run_type === 'llm').length,
    toolCalls: runs.filter(r => r.run_type === 'tool').length,
    chainCalls: runs.filter(r => r.run_type === 'chain').length,
    errors: runs.filter(r => r.error).length,
    totalTokens: sum(runs.map(r => r.total_tokens)),
    totalLatency: sum(runs.map(r => latency(r)))
}
```

## Color Coding System

```javascript
// Run Types
LLM (llm):          #3B82F6 (Blue)    - Expensive, token-heavy
Tool (tool):        #10B981 (Green)   - Fast, no tokens
Chain (chain):      #8B5CF6 (Purple)  - Orchestration
Retriever:          #F59E0B (Orange)  - RAG operations

// Status
Error:              #EF4444 (Red)     - Border color
Success:            #10B981 (Green)   - Checkmark
Pending:            #F59E0B (Orange)  - In progress
```

## Node Sizing Algorithm

```
Base Width:  180px
Base Height: 120px

Width  = 180 + (latency_seconds * 5) + (tokens / 1000 * 3)
Height = 120 + (latency_seconds * 2)

Examples:
- Fast tool (0.5s, 0 tokens):    W=183px, H=121px
- Medium LLM (2s, 2000 tokens):  W=196px, H=124px
- Slow LLM (5s, 5000 tokens):    W=210px, H=130px
```

## API Integration

### Backend Endpoints

**1. List Traces** (`GET /api/traces`):
```python
runs = langsmith_client.list_runs(
    project_name=project_name,
    limit=50,
    order="-start_time"
)

# Filter root runs only
traces = [run for run in runs if not run.parent_run_id]
```

**2. Get Trace Details** (`GET /api/traces/{run_id}`):
```python
def fetch_run_tree(run_id):
    run = langsmith_client.read_run(run_id)
    runs_data.append(run.to_dict())

    for child_id in run.child_run_ids:
        fetch_run_tree(child_id)  # Recursive
```

**3. Get Latest** (`GET /api/traces/latest`):
```python
runs = langsmith_client.list_runs(
    project_name=project_name,
    limit=1,
    order="-start_time",
    filter='eq(parent_run_id, null)'
)
```

### Frontend API Calls

```javascript
// api.js
export const fetchLatestTrace = async () => {
    const response = await axios.get('/api/traces/latest');
    return response.data;
};

// TraceVisualizer.jsx
const loadTrace = async () => {
    const response = await fetchLatestTrace();
    const { nodes, edges } = processTraceData(response.trace);
    setNodes(nodes);
    setEdges(edges);
};
```

## Performance Optimizations

### 1. Efficient Tree Building
- Single pass to create run map
- Single pass to build relationships
- O(n) complexity

### 2. Lazy Loading
- Only fetch trace details when needed
- Don't fetch all runs at startup
- Cache processed data

### 3. React Flow Optimizations
- Use `fitView` to auto-zoom
- Virtualized rendering (React Flow handles this)
- Memoized node components

### 4. Data Transformation
- Process data once, not on every render
- Store processed nodes/edges in state
- Only recalculate on new data

## Error Handling

### Backend Errors
```python
try:
    runs = langsmith_client.list_runs(...)
except Exception as e:
    return jsonify({
        "success": False,
        "error": str(e)
    }), 500
```

### Frontend Errors
```javascript
try {
    const response = await fetchLatestTrace();
    // Process...
} catch (err) {
    setError(err.message);
}
```

### Visual Error Indicators
- Red border on error nodes
- Error badge in node
- Full error message in sidebar
- Error count in stats panel

## Testing with Mock Data

Use `mockData.js` to test without LangSmith:

```javascript
// In TraceVisualizer.jsx
import { mockTraceData } from '../utils/mockData';

// Comment out API call, use mock data instead
// const response = await fetchLatestTrace();
const response = { success: true, trace: mockTraceData };
```

## Future Enhancements

### Technical Improvements
- WebSocket for real-time updates
- Service worker for offline mode
- IndexedDB for trace caching
- Virtual scrolling for large graphs

### Feature Additions
- Search/filter nodes
- Collapse/expand subtrees
- Export graph as image
- Compare multiple traces
- Time-series visualization
- Cost breakdown charts

## Deployment

### Production Build
```bash
npm run build
```

Output in `dist/` folder.

### Serve with Flask
Add to `api.py`:
```python
from flask import send_from_directory

@app.route('/graph')
def serve_graph():
    return send_from_directory('graph-ui/dist', 'index.html')
```

### Environment Variables
```
VITE_API_URL=http://localhost:5000  # API endpoint
```

## Debugging

### Enable Verbose Logging

**Backend**:
```python
logging.basicConfig(level=logging.DEBUG)
```

**Frontend**:
```javascript
console.log('Trace data:', traceData);
console.log('Processed nodes:', nodes);
console.log('Processed edges:', edges);
```

### Browser DevTools
- F12 → Console for errors
- F12 → Network for API calls
- F12 → React DevTools for component state

### Common Issues

**Nodes not showing**:
- Check `processTraceData()` output
- Verify nodes have valid positions
- Check React Flow console warnings

**Edges not connecting**:
- Verify source/target IDs match node IDs
- Check parent/child relationships in data
- Ensure IDs are strings, not numbers

**Layout issues**:
- Adjust `levelSpacing` and `nodeSpacing`
- Check yOffset calculation
- Use `fitView` prop

---

This implementation provides a complete, production-ready trace visualization system that integrates seamlessly with your multi-agent LangSmith-traced application.
