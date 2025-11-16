import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import CustomNode from './CustomNode';
import NodeSidebar from './NodeSidebar';
import StatsPanel from './StatsPanel';
import ChatPanel from './ChatPanel';
import { fetchTraceDetails, fetchTraceRuns } from '../services/api';
import { processTraceData, getTraceStats } from '../utils/traceProcessor';

const nodeTypes = {
  custom: CustomNode,
};

const TraceVisualizer = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [traceStats, setTraceStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availableTraces, setAvailableTraces] = useState([]);
  const [selectedTraceId, setSelectedTraceId] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [runMap, setRunMap] = useState(new Map());
  const [groundingScores, setGroundingScores] = useState({});
  const [isCalculatingGrounding, setIsCalculatingGrounding] = useState(false);

  // Load available traces on mount
  useEffect(() => {
    loadAvailableTraces();
  }, []);

  const loadAvailableTraces = async () => {
    try {
      const response = await fetchTraceRuns();
      if (response.success && response.traces) {
        setAvailableTraces(response.traces);
      }
    } catch (err) {
      console.error('Error loading traces:', err);
    }
  };

  const clearTraceView = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setTraceStats(null);
    setSelectedNode(null);
  }, [setNodes, setEdges]);

  const loadTrace = async (traceId) => {
    if (!traceId) {
      clearTraceView();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetchTraceDetails(traceId);

      if (response.success && response.trace) {
        const { nodes: processedNodes, edges: processedEdges, runMap: processedRunMap } = processTraceData(response.trace);
        setNodes(processedNodes);
        setEdges(processedEdges);
        setRunMap(processedRunMap);
        setTraceStats(getTraceStats(response.trace));
      } else {
        setError(response.error || 'Failed to load trace data');
        clearTraceView();
      }
    } catch (err) {
      console.error('Error loading trace:', err);
      setError(err.message || 'Failed to load trace');
      clearTraceView();
    } finally {
      setLoading(false);
    }
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleRefresh = () => {
    if (selectedTraceId) {
      loadTrace(selectedTraceId);
    }
    loadAvailableTraces();
  };

  const handleTraceSelect = (traceId) => {
    if (!traceId) {
      setSelectedTraceId(null);
      clearTraceView();
      return;
    }

    setSelectedTraceId(traceId);
    loadTrace(traceId);
  };

  const handleCalculateGrounding = async () => {
    if (nodes.length === 0) {
      setError('No trace loaded. Please select a trace first.');
      return;
    }

    setIsCalculatingGrounding(true);
    setError(null);

    try {
      // Convert nodes to plain data format for API
      const nodesData = Array.from(runMap.values());

      const response = await fetch('http://localhost:8000/api/grounding', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ nodes: nodesData }),
      });

      const result = await response.json();

      if (result.success) {
        setGroundingScores(result.scores);

        // Helper function to map grounding score (1-10) to color (red to green)
        const getGroundingColor = (score) => {
          if (!score) return null;
          const ratio = (score - 1) / 9; // Normalize to 0-1
          const r = Math.round(239 - (239 - 16) * ratio);
          const g = Math.round(68 + (185 - 68) * ratio);
          const b = Math.round(68 + (129 - 68) * ratio);
          return `rgb(${r}, ${g}, ${b})`;
        };

        // Update node styles with grounding scores and reasoning
        setNodes(nodes.map(node => {
          const groundingData = result.scores[node.id];
          const score = groundingData?.score;
          const reasoning = groundingData?.reasoning;
          const groundingColor = score ? getGroundingColor(score) : null;

          return {
            ...node,
            data: {
              ...node.data,
              groundingScore: score,
              groundingReasoning: reasoning
            },
            style: {
              ...node.style,
              border: groundingColor
                ? `8px solid ${groundingColor}`
                : node.data.error
                  ? "3px solid #EF4444"
                  : "2px solid #E5E7EB"
            }
          };
        }));
      } else {
        setError(result.error || 'Failed to calculate grounding scores');
      }
    } catch (err) {
      console.error('Error calculating grounding:', err);
      setError(err.message || 'Failed to calculate grounding scores');
    } finally {
      setIsCalculatingGrounding(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '15px 20px',
        backgroundColor: '#1F2937',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          {/* Chat Button */}
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            style={{
              padding: '10px',
              backgroundColor: isChatOpen ? '#3B82F6' : '#374151',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '20px',
              lineHeight: '1',
              transition: 'background-color 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Open Trace Assistant"
          >
            💬
          </button>

          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
              🔍 LangSmith Trace Visualizer
            </h1>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', opacity: 0.8 }}>
              Interactive trace graph with detailed node inspection
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Trace selector */}
          {availableTraces.length > 0 && (
            <select
              value={selectedTraceId || ''}
              onChange={(e) => handleTraceSelect(e.target.value)}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #D1D5DB',
                fontSize: '13px',
                backgroundColor: 'white',
                color: '#111827',
                cursor: 'pointer'
              }}
            >
              <option value="">Select a trace...</option>
              {availableTraces.map(trace => (
                <option key={trace.id} value={trace.id}>
                  {trace.name} - {new Date(trace.start_time).toLocaleString()}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleRefresh}
            disabled={loading}
            style={{
              padding: '8px 16px',
              backgroundColor: '#3B82F6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? '🔄 Loading...' : '🔄 Refresh'}
          </button>

          <button
            onClick={handleCalculateGrounding}
            disabled={isCalculatingGrounding || nodes.length === 0}
            style={{
              padding: '8px 16px',
              backgroundColor: '#10B981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: isCalculatingGrounding || nodes.length === 0 ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              opacity: isCalculatingGrounding || nodes.length === 0 ? 0.6 : 1
            }}
          >
            {isCalculatingGrounding ? '⚙️ Calculating...' : '📊 Calculate Grounding'}
          </button>
        </div>
      </div>

      {/* Stats Panel */}
      {traceStats && <StatsPanel stats={traceStats} />}

      {/* Error Display */}
      {error && (
        <div style={{
          padding: '15px',
          margin: '10px 20px',
          backgroundColor: '#FEE2E2',
          border: '1px solid #EF4444',
          borderRadius: '6px',
          color: '#991B1B'
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Main Graph Area */}
      <div style={{ flex: 1, position: 'relative' }}>
        {loading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            fontSize: '18px',
            color: '#6B7280'
          }}>
            Loading trace data...
          </div>
        ) : nodes.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            color: '#6B7280'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>📊</div>
            <div style={{ fontSize: '18px', marginBottom: '10px' }}>No trace data available</div>
            <div style={{ fontSize: '14px', opacity: 0.7 }}>
              Run a query through the API to generate trace data
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#aaa" gap={16} />
            <Controls />
            <MiniMap
              nodeColor={(node) => node.style?.backgroundColor || '#6B7280'}
              style={{
                backgroundColor: '#F9FAFB',
                border: '1px solid #D1D5DB'
              }}
            />
          </ReactFlow>
        )}
      </div>

      {/* Sidebar */}
      {selectedNode && (
        <NodeSidebar
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {/* Chat Panel */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        nodes={nodes}
        runMap={runMap}
      />

      {/* Node Type Legend */}
      <div style={{
        position: 'absolute',
        bottom: '20px',
        left: '20px',
        backgroundColor: 'white',
        padding: '12px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        fontSize: '12px',
        zIndex: 5
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Node Types</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '20px', height: '20px', backgroundColor: '#3B82F6', borderRadius: '4px' }} />
            <span>LLM</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '20px', height: '20px', backgroundColor: '#10B981', borderRadius: '4px' }} />
            <span>Tool</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '20px', height: '20px', backgroundColor: '#8B5CF6', borderRadius: '4px' }} />
            <span>Chain</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '20px', height: '20px', backgroundColor: '#F59E0B', borderRadius: '4px' }} />
            <span>Retriever</span>
          </div>
        </div>
      </div>

      {/* Grounding Score Legend */}
      {Object.keys(groundingScores).length > 0 && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '20px',
          transform: 'translateY(-50%)',
          backgroundColor: 'white',
          padding: '12px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          fontSize: '12px',
          zIndex: 5
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px', textAlign: 'center' }}>Grounding Score</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            {/* Score label at top */}
            <div style={{ fontSize: '11px', fontWeight: '600', color: '#10B981' }}>10</div>

            {/* Gradient bar */}
            <div style={{
              width: '30px',
              height: '150px',
              background: 'linear-gradient(to bottom, rgb(16, 185, 129) 0%, rgb(239, 68, 68) 100%)',
              borderRadius: '4px',
              border: '1px solid #D1D5DB'
            }} />

            {/* Score label at bottom */}
            <div style={{ fontSize: '11px', fontWeight: '600', color: '#EF4444' }}>1</div>

            {/* Description */}
            <div style={{
              fontSize: '10px',
              color: '#6B7280',
              marginTop: '4px',
              textAlign: 'center',
              maxWidth: '100px'
            }}>
              How grounded LLM responses are in tool outputs
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TraceVisualizer;
