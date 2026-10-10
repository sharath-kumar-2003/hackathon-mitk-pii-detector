import React from 'react';

export default function Overview({ metrics }) {
  if (!metrics || !metrics.has_data) {
    return (
      <div className="card empty-state">
        <div className="empty-title">Not Evaluated Yet</div>
        <p>Run the evaluation benchmark or test queries in the Test Lab to populate security metrics.</p>
      </div>
    );
  }

  const reqSummary = metrics.requests_summary || { allowed: 0, sanitized: 0, blocked: 0 };
  const detAnalytics = metrics.detection_analytics || {};
  const leakAnalytics = metrics.leakage_prevention || {};
  const restAnalytics = metrics.restoration_analytics || {};
  const perfAnalytics = metrics.performance_analytics || {};

  return (
    <div>
      <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
        <div className="metric-card">
          <div className="metric-label">Total Requests</div>
          <div className="metric-value">{metrics.total_requests}</div>
          <div className="metric-subtext">Processed by Gateway</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">PII Detection Rate</div>
          <div className="metric-value">
            {detAnalytics.detection_rate_pct != null ? `${detAnalytics.detection_rate_pct}%` : `${detAnalytics.total_pii_detected || 0} PII`}
          </div>
          <div className="metric-subtext">Precision: {detAnalytics.precision != null ? detAnalytics.precision : 'N/A'} | F1: {detAnalytics.f1_score != null ? detAnalytics.f1_score : 'N/A'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Leakage Prevention</div>
          <div className="metric-value">
            {leakAnalytics.leakage_prevention_rate_pct != null ? `${leakAnalytics.leakage_prevention_rate_pct}%` : '100%'}
          </div>
          <div className="metric-subtext">{leakAnalytics.leakage_count != null ? `${leakAnalytics.leakage_count} leaks` : '0 leaks detected'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Added Latency</div>
          <div className="metric-value">
            {perfAnalytics.avg_added_ms != null ? `${perfAnalytics.avg_added_ms} ms` : 'N/A'}
          </div>
          <div className="metric-subtext">p95 Total: {perfAnalytics.p95_protected_ms || 0} ms</div>
        </div>
      </div>

      <div className="grid-cols-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Security Decision Distribution</span>
          </div>
          <div style={{ display: 'flex', gap: '0.85rem', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-success">ALLOWED</span> Permitted Payload
              </span>
              <strong>{reqSummary.allowed || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-warning">REDACTED</span> PII Masked & Anonymized
              </span>
              <strong>{reqSummary.redacted != null ? reqSummary.redacted : (reqSummary.sanitized || 0)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-info">TOKENIZED</span> Vault Tokenized
              </span>
              <strong>{reqSummary.tokenized != null ? reqSummary.tokenized : 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-danger">BLOCKED</span> Policy Violation
              </span>
              <strong>{reqSummary.blocked || 0}</strong>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Token Vault & Authorization</span>
          </div>
          <div style={{ display: 'flex', gap: '0.85rem', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Active Vault Tokens</span>
              <strong>{restAnalytics.active_tokens_in_vault || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Authorized Restorations</span>
              <strong>{restAnalytics.successful_restorations || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Unauthorized Restorations</span>
              <strong style={{ color: 'var(--danger)' }}>{restAnalytics.cross_session_attempts || 0}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
