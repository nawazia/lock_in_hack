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
import { fetchLatestTrace, fetchTraceDetails, fetchTraceRuns } from '../services/api';
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

  const loadTrace = async (traceId = null) => {
    setLoading(true);
    setError(null);

    try {
      let response;
      if (traceId) {
        response = await fetchTraceDetails(traceId);
      } else {
        response = await fetchLatestTrace();
      }

      if (response.success && response.trace) {
        const { nodes: processedNodes, edges: processedEdges } = processTraceData(response.trace);
        setNodes(processedNodes);
        setEdges(processedEdges);
        setTraceStats(getTraceStats(response.trace));
        setSelectedTraceId(response.trace.run_id || traceId);
      } else {
        setError(response.error || 'Failed to load trace data');
      }
    } catch (err) {
      console.error('Error loading trace:', err);
      setError(err.message || 'Failed to load trace');
    } finally {
      setLoading(false);
    }
  };

  // Load latest trace on mount
  useEffect(() => {
    loadTrace();
  }, []);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleRefresh = () => {
    loadTrace(selectedTraceId);
    loadAvailableTraces();
  };

  const handleTraceSelect = (traceId) => {
    loadTrace(traceId);
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
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
            🔍 LangSmith Trace Visualizer
          </h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', opacity: 0.8 }}>
            Interactive trace graph with detailed node inspection
          </p>
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

      {/* Legend */}
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
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Legend</div>
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
    </div>
  );
};

export default TraceVisualizer;
