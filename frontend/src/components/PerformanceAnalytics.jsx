import React from 'react';

export default function PerformanceAnalytics({ metrics }) {
  if (!metrics || !metrics.performance_analytics) {
    return (
      <div className="card empty-state">
        <div className="empty-title">No Performance Metrics Available</div>
        <p>Run evaluation or process simulation requests to measure latency and stage timing metrics.</p>
      </div>
    );
  }

  const perf = metrics.performance_analytics;
  const stages = perf.stage_averages || {};

  return (
    <div>
      <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
        <div className="metric-card">
          <div className="metric-label">Direct Baseline</div>
          <div className="metric-value">{perf.avg_baseline_ms != null ? `${perf.avg_baseline_ms} ms` : '0 ms'}</div>
          <div className="metric-subtext">Unprotected execution</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Protected Path (Median)</div>
          <div className="metric-value">
            {perf.median_protected_ms != null ? `${perf.median_protected_ms} ms` : '0 ms'}
          </div>
          <div className="metric-subtext">50th percentile total duration</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Protected Path (p95)</div>
          <div className="metric-value">
            {perf.p95_protected_ms != null ? `${perf.p95_protected_ms} ms` : '0 ms'}
          </div>
          <div className="metric-subtext">95th percentile latency</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Added Latency</div>
          <div className="metric-value">
            {perf.avg_added_ms != null ? `${perf.avg_added_ms} ms` : '0 ms'}
          </div>
          <div className="metric-subtext">Firewall processing overhead</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Firewall Pipeline Stage Breakdown (Average Latency)</span>
        </div>
        <div className="grid-cols-4">
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>1. Policy Engine</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.2rem' }}>{stages.policy_ms || 0} ms</div>
          </div>
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>2. PII Detection</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.2rem' }}>{stages.detection_ms || 0} ms</div>
          </div>
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>3. Transformation</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.2rem' }}>{stages.transformation_ms || 0} ms</div>
          </div>
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: '4px' }}>
            <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>4. Outbound Verification</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.2rem' }}>{stages.verification_ms || 0} ms</div>
          </div>
        </div>
      </div>
    </div>
  );
}
