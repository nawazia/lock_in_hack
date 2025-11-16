import React from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data, selected }) => {
  const { name, runType, latencyFormatted, totalTokens, error, isCollapsed } = data;

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

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        color: 'white',
        fontSize: '13px',
        boxShadow: selected ? '0 0 0 3px #60A5FA' : 'none',
        transition: 'all 0.2s',
        position: 'relative'
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#555' }}
      />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <span style={{ fontSize: '18px' }}>{getIcon()}</span>
        <span style={{
          fontSize: '15px',
          fontWeight: '600',
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: '1.3'
        }}>
          {name}
        </span>
      </div>

      {/* Type */}
      <div style={{
        fontSize: '11px',
        opacity: 0.75,
        textTransform: 'uppercase',
        marginBottom: '8px',
        letterSpacing: '0.5px'
      }}>
        {runType || 'unknown'}
      </div>

      {/* Metrics */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
        {latencyFormatted && latencyFormatted !== 'N/A' && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ opacity: 0.9 }}>⏱️</span>
            <span style={{ fontWeight: '600' }}>{latencyFormatted}</span>
          </div>
        )}
        {totalTokens > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ opacity: 0.9 }}>🔤</span>
            <span style={{ fontWeight: '600' }}>{totalTokens.toLocaleString()}</span>
          </div>
        )}
      </div>

      {/* Collapsed indicator */}
      {isCollapsed && (
        <div style={{
          marginTop: '8px',
          padding: '4px 6px',
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: '600',
          textAlign: 'center'
        }}>
          📦 COLLAPSED
        </div>
      )}

      {/* Error indicator */}
      {error && (
        <div style={{
          marginTop: '8px',
          padding: '4px 6px',
          background: 'rgba(239, 68, 68, 0.3)',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: '700',
          textAlign: 'center'
        }}>
          ❌ ERROR
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
