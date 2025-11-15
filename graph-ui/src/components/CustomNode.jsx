import React from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data, selected }) => {
  const { name, runType, status, latencyFormatted, totalTokens, error } = data;

  // Icon based on run type
  const getIcon = () => {
    switch (runType) {
      case 'llm':
        return '🤖';
      case 'tool':
        return '🔧';
      case 'chain':
        return '⛓️';
      case 'retriever':
        return '🔍';
      default:
        return '📦';
    }
  };

  // Status indicator
  const getStatusIndicator = () => {
    if (error) return '❌';
    if (status === 'success') return '✅';
    return '⏳';
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        color: 'white',
        fontSize: '12px',
        boxShadow: selected ? '0 0 0 3px #60A5FA' : 'none',
        transition: 'all 0.2s'
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#555' }}
      />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <span style={{ fontSize: '16px' }}>{getIcon()}</span>
        <span style={{ fontSize: '14px', fontWeight: 'bold', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {name}
        </span>
        <span style={{ fontSize: '14px' }}>{getStatusIndicator()}</span>
      </div>

      {/* Type */}
      <div style={{
        fontSize: '10px',
        opacity: 0.8,
        textTransform: 'uppercase',
        marginBottom: '6px'
      }}>
        {runType}
      </div>

      {/* Metrics */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '11px' }}>
        {latencyFormatted && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>⏱️ Latency:</span>
            <span style={{ fontWeight: 'bold' }}>{latencyFormatted}</span>
          </div>
        )}
        {totalTokens > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>🔤 Tokens:</span>
            <span style={{ fontWeight: 'bold' }}>{totalTokens.toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* Error indicator */}
      {error && (
        <div style={{
          marginTop: '6px',
          padding: '4px',
          background: 'rgba(239, 68, 68, 0.3)',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold'
        }}>
          ERROR
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#555' }}
      />
    </div>
  );
};

export default CustomNode;
