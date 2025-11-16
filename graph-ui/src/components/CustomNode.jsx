import React from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data, selected }) => {
  const { name, runType, latencyFormatted, totalTokens, error, isCollapsed, collapsedCount, collapsedNodes, modelName, groundingScore } = data;

  // Map grounding score (1-10) to color (red to green)
  const getGroundingColor = (score) => {
    if (!score) return null;

    // Interpolate between red (1) and green (10)
    // Red: rgb(239, 68, 68) - #EF4444
    // Green: rgb(16, 185, 129) - #10B981
    const ratio = (score - 1) / 9; // Normalize to 0-1

    const r = Math.round(239 - (239 - 16) * ratio);
    const g = Math.round(68 + (185 - 68) * ratio);
    const b = Math.round(68 + (129 - 68) * ratio);

    return `rgb(${r}, ${g}, ${b})`;
  };

  const groundingColor = groundingScore ? getGroundingColor(groundingScore) : null;

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

      {/* Type and Model */}
      <div style={{
        fontSize: '11px',
        opacity: 0.75,
        marginBottom: '8px',
        letterSpacing: '0.5px',
        display: 'flex',
        flexDirection: 'column',
        gap: '2px'
      }}>
        <div style={{ textTransform: 'uppercase' }}>
          {runType || 'unknown'}
        </div>
        {modelName && (
          <div style={{
            fontSize: '10px',
            opacity: 0.9,
            fontWeight: '500',
            textTransform: 'none'
          }}>
            {modelName}
          </div>
        )}
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
          📦 +{collapsedCount} {collapsedCount === 1 ? 'node' : 'nodes'}
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
