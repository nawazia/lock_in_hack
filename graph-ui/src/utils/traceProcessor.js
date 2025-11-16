/**
 * Process LangSmith trace data into React Flow nodes and edges
 */

// Color mapping based on run type
const RUN_TYPE_COLORS = {
  llm: "#3B82F6", // Blue
  tool: "#10B981", // Green
  chain: "#8B5CF6", // Purple
  retriever: "#F59E0B", // Orange
  default: "#6B7280", // Gray
};

// Status colors
const STATUS_COLORS = {
  success: "#10B981", // Green
  error: "#EF4444", // Red
  pending: "#F59E0B", // Orange
};

/**
 * Calculate node size based on latency and token count
 */
const calculateNodeSize = (run) => {
  const baseSize = 180;
  const latency =
    run.end_time && run.start_time
      ? new Date(run.end_time) - new Date(run.start_time)
      : 0;

  const totalTokens = run.total_tokens || 0;

  // Size based on latency (ms) and tokens
  const latencyFactor = Math.min(latency / 1000, 10); // Cap at 10s
  const tokenFactor = Math.min(totalTokens / 1000, 10); // Cap at 10k tokens

  const width = baseSize + latencyFactor * 5 + tokenFactor * 3;
  const height = 120 + latencyFactor * 2;

  return { width: 250, height: 150 };
};

/**
 * Get color for a node based on type and status
 */
const getNodeColor = (run) => {
  if (run.error) {
    return STATUS_COLORS.error;
  }

  const runType = run.runType || "default";
  return RUN_TYPE_COLORS[runType] || RUN_TYPE_COLORS.default;
};

/**
 * Format latency in human-readable form
 */
export const formatLatency = (startTime, endTime) => {
  if (!startTime || !endTime) return "N/A";

  const latencyMs = new Date(endTime) - new Date(startTime);

  if (latencyMs < 1000) {
    return `${latencyMs}ms`;
  } else if (latencyMs < 60000) {
    return `${(latencyMs / 1000).toFixed(2)}s`;
  } else {
    const minutes = Math.floor(latencyMs / 60000);
    const seconds = ((latencyMs % 60000) / 1000).toFixed(0);
    return `${minutes}m ${seconds}s`;
  }
};

/**
 * Extract model name from LLM outputs
 */
const extractModelName = (run) => {
  if (run.run_type !== 'llm' || !run.outputs) {
    return null;
  }

  try {
    // Try to get model_name from llm_output
    if (run.outputs.llm_output && run.outputs.llm_output.model_name) {
      return run.outputs.llm_output.model_name;
    }

    // Try to get from generations response_metadata
    if (run.outputs.generations &&
        Array.isArray(run.outputs.generations) &&
        run.outputs.generations[0] &&
        Array.isArray(run.outputs.generations[0]) &&
        run.outputs.generations[0][0] &&
        run.outputs.generations[0][0].message &&
        run.outputs.generations[0][0].message.kwargs &&
        run.outputs.generations[0][0].message.kwargs.response_metadata &&
        run.outputs.generations[0][0].message.kwargs.response_metadata.model_name) {
      return run.outputs.generations[0][0].message.kwargs.response_metadata.model_name;
    }
  } catch (e) {
    // If any error occurs during extraction, just return null
    return null;
  }

  return null;
};

/**
 * Extract key metrics from a run
 */
const extractMetrics = (run) => {
  const latency =
    run.end_time && run.start_time
      ? new Date(run.end_time) - new Date(run.start_time)
      : null;

  return {
    id: run.id,
    name: run.name,
    runType: run.run_type,
    status: run.error ? "error" : run.end_time ? "success" : "pending",
    startTime: run.start_time,
    endTime: run.end_time,
    latency: latency,
    latencyFormatted: formatLatency(run.start_time, run.end_time),
    inputs: run.inputs,
    outputs: run.outputs,
    error: run.error,
    tags: run.tags || [],
    metadata: run.extra?.metadata || {},
    totalTokens: run.total_tokens,
    promptTokens: run.prompt_tokens,
    completionTokens: run.completion_tokens,
    feedbackStats: run.feedback_stats || {},
    parentRunId: run.parent_run_id,
    childRunIds: run.child_run_ids || [],
    events: run.events || [],
    modelName: extractModelName(run),
  };
};

/**
 * Build a hierarchical tree from flat trace data
 */
const buildTraceTree = (runs) => {
  const runMap = new Map();
  const rootRuns = [];

  // First pass: create map of all runs
  runs.forEach((run) => {
    const metrics = extractMetrics(run);
    runMap.set(run.id, { ...metrics, children: [] });
  });

  // Second pass: build parent-child relationships
  runs.forEach((run) => {
    const node = runMap.get(run.id);
    if (run.parent_run_id && runMap.has(run.parent_run_id)) {
      const parent = runMap.get(run.parent_run_id);
      parent.children.push(node);
    } else {
      rootRuns.push(node);
    }
  });

  return { runMap, rootRuns };
};

/**
 * Compress single-child chains with the same run type.
 *
 * Example: A -> B -> C -> D (where D has multiple children)
 * If A, B, C, D all have same runType, compress to just A pointing to D's children.
 */
const compressChains = (node) => {
  // Recursively compress children first
  node.children.forEach((child) => compressChains(child));

  // Check if we should compress this chain
  // Start from current node and walk down single-child chain
  let current = node;
  let chainNodes = [current];

  // Walk down the chain while:
  // 1. Current node has exactly one child
  // 2. Child has same runType as the chain start
  while (
    current.children.length === 1 &&
    current.children[0].runType === node.runType
  ) {
    current = current.children[0];
    chainNodes.push(current);
  }

  // If we found a chain (more than just the original node), compress it
  if (chainNodes.length > 1) {
    // Keep the first node in the chain (the current node)
    // Point it directly to the last node's children
    const lastNode = chainNodes[chainNodes.length - 1];

    // Mark the first node as collapsed and store compressed count
    node.isCollapsed = true;
    node.collapsedCount = chainNodes.length - 1;
    node.collapsedNodes = chainNodes.slice(1).map((n) => n.name);

    // Replace children: skip all intermediate nodes, use last node's children
    node.children = lastNode.children;
  }

  return node;
};

/**
 * Convert tree to React Flow nodes and edges
 */
const treeToFlowGraph = (rootRuns, runMap) => {
  const nodes = [];
  const edges = [];

  let yOffset = 0;
  const levelSpacing = 300;
  const nodeSpacing = 10;

  const processNode = (node, level = 0, xOffset = 0, parentId = null) => {
    const size = calculateNodeSize(node);
    const color = getNodeColor(node);

    // Create React Flow node
    const flowNode = {
      id: node.id,
      type: "custom",
      position: { x: level * levelSpacing, y: yOffset },
      data: {
        ...node,
        color: color,
        size: size,
      },
      style: {
        width: size.width,
        height: size.height,
        backgroundColor: color,
        border: node.error ? "3px solid #EF4444" : "2px solid #E5E7EB",
        borderRadius: "8px",
        padding: "10px",
      },
    };

    nodes.push(flowNode);

    // Create edge from parent
    if (parentId) {
      edges.push({
        id: `${parentId}-${node.id}`,
        source: parentId,
        target: node.id,
        type: "smoothstep",
        animated: node.runType === "llm",
        style: {
          stroke: color,
          strokeWidth: 2,
        },
      });
    }

    // Process children
    node.children.forEach((child, i) => {
      processNode(child, level + 1, xOffset, node.id);
      if (node.children.length > 1) {
        yOffset += size.height + nodeSpacing;
      }
    });
  };

  // Process all root nodes
  rootRuns.forEach((root) => {
    processNode(root, 0, 0, null);
  });

  return { nodes, edges };
};

/**
 * Main function to process trace data
 */
export const processTraceData = (traceData) => {
  if (!traceData || !traceData.runs || traceData.runs.length === 0) {
    return { nodes: [], edges: [], runMap: new Map() };
  }
  print(traceData.runs);
  const { runMap, rootRuns } = buildTraceTree(traceData.runs);

  // Compress single-child chains with same run type
  rootRuns.forEach((root) => compressChains(root));

  const { nodes, edges } = treeToFlowGraph(rootRuns, runMap);

  return { nodes, edges, runMap };
};

/**
 * Get statistics from trace data
 */
export const getTraceStats = (traceData) => {
  if (!traceData || !traceData.runs) {
    return null;
  }

  const runs = traceData.runs;

  // Find the root run (no parent_run_id)
  const rootRun = runs.find((r) => !r.parent_run_id);

  const totalRuns = runs.length;
  const llmCalls = runs.filter((r) => r.run_type === "llm").length;
  const toolCalls = runs.filter((r) => r.run_type === "tool").length;
  const chainCalls = runs.filter((r) => r.run_type === "chain").length;
  const errors = runs.filter((r) => r.error).length;

  // Use root run's values (which are cumulative) instead of summing all runs
  const totalTokens = rootRun?.total_tokens || 0;
  const totalLatency =
    rootRun?.start_time && rootRun?.end_time
      ? new Date(rootRun.end_time) - new Date(rootRun.start_time)
      : 0;

  return {
    totalRuns,
    llmCalls,
    toolCalls,
    chainCalls,
    errors,
    totalTokens,
    totalLatency: formatLatency(rootRun?.start_time, rootRun?.end_time),
  };
};
