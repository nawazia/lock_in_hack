import React from 'react';

const StatsPanel = ({ stats }) => {
  if (!stats) return null;

  const StatCard = ({ icon, label, value, color = '#3B82F6' }) => (
    <div style={{
      flex: 1,
      padding: '12px 16px',
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      borderLeft: `4px solid ${color}`
    }}>
      <div style={{ fontSize: '11px', color: '#6B7280', textTransform: 'uppercase', fontWeight: '500' }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827' }}>
        {value}
      </div>
    </div>
  );

  return (
    <div style={{
      padding: '15px 20px',
      backgroundColor: '#F9FAFB',
      borderBottom: '1px solid #E5E7EB',
      display: 'flex',
      gap: '12px',
      overflowX: 'auto'
    }}>
      <StatCard
        icon="📊"
        label="Total Runs"
        value={stats.totalRuns}
        color="#6B7280"
      />
      <StatCard
        icon="🤖"
        label="LLM Calls"
        value={stats.llmCalls}
        color="#3B82F6"
      />
      <StatCard
        icon="🔧"
        label="Tool Calls"
        value={stats.toolCalls}
        color="#10B981"
      />
      <StatCard
        icon="⛓️"
        label="Chain Calls"
        value={stats.chainCalls}
        color="#8B5CF6"
      />
      {stats.errors > 0 && (
        <StatCard
          icon="❌"
          label="Errors"
          value={stats.errors}
          color="#EF4444"
        />
      )}
      <StatCard
        icon="🔤"
        label="Total Tokens"
        value={stats.totalTokens.toLocaleString()}
        color="#F59E0B"
      />
      <StatCard
        icon="⏱️"
        label="Total Time"
        value={stats.totalLatency}
        color="#EC4899"
      />
    </div>
  );
};

export default StatsPanel;
