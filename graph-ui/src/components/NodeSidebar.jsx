import React from 'react';
import { X } from 'lucide-react';

const NodeSidebar = ({ node, onClose }) => {
  if (!node) return null;

  const {
    name,
    runType,
    status,
    startTime,
    endTime,
    latencyFormatted,
    inputs,
    outputs,
    error,
    tags,
    metadata,
    totalTokens,
    promptTokens,
    completionTokens,
    feedbackStats,
    groundingScore,
    groundingReasoning
  } = node.data;

  const formatJson = (obj) => {
    if (!obj) return 'N/A';
    if (typeof obj === 'string') return obj;
    return JSON.stringify(obj, null, 2);
  };

  const Section = ({ title, children }) => (
    <div style={{ marginBottom: '20px' }}>
      <h3 style={{
        fontSize: '14px',
        fontWeight: 'bold',
        marginBottom: '8px',
        color: '#1F2937',
        borderBottom: '2px solid #E5E7EB',
        paddingBottom: '4px'
      }}>
        {title}
      </h3>
      {children}
    </div>
  );

  const InfoRow = ({ label, value, mono = false }) => (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ fontSize: '11px', color: '#6B7280', marginBottom: '2px' }}>
        {label}
      </div>
      <div style={{
        fontSize: '13px',
        color: '#111827',
        fontFamily: mono ? 'monospace' : 'inherit',
        wordBreak: 'break-word'
      }}>
        {value || 'N/A'}
      </div>
    </div>
  );

  return (
    <div style={{
      position: 'fixed',
      right: 0,
      top: 0,
      bottom: 0,
      width: '450px',
      backgroundColor: 'white',
      boxShadow: '-4px 0 6px rgba(0, 0, 0, 0.1)',
      overflowY: 'auto',
      zIndex: 1000,
      padding: '20px'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        paddingBottom: '10px',
        borderBottom: '2px solid #E5E7EB'
      }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#111827' }}>
          Run Details
        </h2>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <X size={24} color="#6B7280" />
        </button>
      </div>

      {/* Basic Info */}
      <Section title="Basic Information">
        <InfoRow label="Name" value={name} />
        <InfoRow label="Type" value={runType?.toUpperCase()} />
        <InfoRow label="Status" value={status?.toUpperCase()} />
        <InfoRow label="Start Time" value={startTime ? new Date(startTime).toLocaleString() : 'N/A'} mono />
        <InfoRow label="End Time" value={endTime ? new Date(endTime).toLocaleString() : 'N/A'} mono />
        <InfoRow label="Latency" value={latencyFormatted} />
      </Section>

      {/* Token Usage (for LLM calls) */}
      {(totalTokens > 0 || promptTokens > 0 || completionTokens > 0) && (
        <Section title="Token Usage">
          {totalTokens > 0 && <InfoRow label="Total Tokens" value={totalTokens.toLocaleString()} />}
          {promptTokens > 0 && <InfoRow label="Prompt Tokens" value={promptTokens.toLocaleString()} />}
          {completionTokens > 0 && <InfoRow label="Completion Tokens" value={completionTokens.toLocaleString()} />}
        </Section>
      )}

      {/* Grounding Analysis */}
      {groundingScore && groundingReasoning && (
        <Section title="Grounding Analysis">
          <InfoRow label="Grounding Score" value={`${groundingScore}/10`} />
          <div style={{ marginTop: '8px' }}>
            <div style={{ fontSize: '11px', color: '#6B7280', marginBottom: '4px' }}>
              Reasoning
            </div>
            <div style={{
              padding: '10px',
              backgroundColor: '#F0FDF4',
              border: '1px solid #86EFAC',
              borderRadius: '6px',
              fontSize: '13px',
              color: '#166534',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {groundingReasoning}
            </div>
          </div>
        </Section>
      )}

      {/* Error */}
      {error && (
        <Section title="Error">
          <div style={{
            padding: '10px',
            backgroundColor: '#FEE2E2',
            border: '1px solid #EF4444',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#991B1B',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {formatJson(error)}
          </div>
        </Section>
      )}

      {/* Tags */}
      {tags && tags.length > 0 && (
        <Section title="Tags">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {tags.map((tag, idx) => (
              <span
                key={idx}
                style={{
                  padding: '4px 8px',
                  backgroundColor: '#DBEAFE',
                  color: '#1E40AF',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: '500'
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Metadata */}
      {metadata && Object.keys(metadata).length > 0 && (
        <Section title="Metadata">
          <pre style={{
            padding: '10px',
            backgroundColor: '#F3F4F6',
            border: '1px solid #D1D5DB',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: 'monospace',
            overflow: 'auto',
            maxHeight: '200px'
          }}>
            {formatJson(metadata)}
          </pre>
        </Section>
      )}

      {/* Inputs */}
      <Section title="Inputs">
        <pre style={{
          padding: '10px',
          backgroundColor: '#F3F4F6',
          border: '1px solid #D1D5DB',
          borderRadius: '6px',
          fontSize: '11px',
          fontFamily: 'monospace',
          overflow: 'auto',
          maxHeight: '300px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {formatJson(inputs)}
        </pre>
      </Section>

      {/* Outputs */}
      <Section title="Outputs">
        <pre style={{
          padding: '10px',
          backgroundColor: '#F3F4F6',
          border: '1px solid #D1D5DB',
          borderRadius: '6px',
          fontSize: '11px',
          fontFamily: 'monospace',
          overflow: 'auto',
          maxHeight: '300px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {formatJson(outputs)}
        </pre>
      </Section>

      {/* Feedback Stats */}
      {feedbackStats && Object.keys(feedbackStats).length > 0 && (
        <Section title="Feedback Statistics">
          <pre style={{
            padding: '10px',
            backgroundColor: '#F3F4F6',
            border: '1px solid #D1D5DB',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: 'monospace',
            overflow: 'auto',
            maxHeight: '150px'
          }}>
            {formatJson(feedbackStats)}
          </pre>
        </Section>
      )}
    </div>
  );
};

export default NodeSidebar;
