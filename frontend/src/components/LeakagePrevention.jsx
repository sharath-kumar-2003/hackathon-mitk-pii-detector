import React from 'react';

export default function LeakagePrevention({ metrics }) {
  if (!metrics || !metrics.leakage_prevention) {
    return (
      <div className="card empty-state">
        <div className="empty-title">No Leakage Prevention Data</div>
        <p>Run the evaluation suite to inspect mock tool payload evidence for protected PII leakage.</p>
      </div>
    );
  }

  const leak = metrics.leakage_prevention;
  const failures = leak.leakage_failures || [];

  return (
    <div>
      <div className="grid-cols-3" style={{ marginBottom: '1.25rem' }}>
        <div className="metric-card">
          <div className="metric-label">Protected PII Tested</div>
          <div className="metric-value">{leak.total_protected_instances || 0}</div>
          <div className="metric-subtext">Across evaluation tool calls</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Leakage-Free Instances</div>
          <div className="metric-value">{leak.leakage_free_instances || 0}</div>
          <div className="metric-subtext">Prevented from reaching tools</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Prevention Rate</div>
          <div className="metric-value">
            {leak.leakage_prevention_rate_pct != null ? `${leak.leakage_prevention_rate_pct}%` : '100%'}
          </div>
          <div className="metric-subtext">{leak.leakage_count || 0} security breaches</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Outbound Verification & Payload Integrity Log</span>
        </div>
        {failures.length === 0 ? (
          <div style={{ padding: '0.85rem 1rem', background: 'var(--success-bg)', border: '1px solid var(--success-border)', borderRadius: '4px', color: 'var(--success)', fontSize: '0.8rem' }}>
            Zero protected PII values leaked to external simulated tools across all evaluated test cases.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Test Case ID</th>
                  <th>Tool Name</th>
                  <th>Leaked Values</th>
                  <th>Received Payload Snapshot</th>
                </tr>
              </thead>
              <tbody>
                {failures.map((f, i) => (
                  <tr key={i}>
                    <td><code>{f.test_case_id}</code></td>
                    <td>{f.tool_name}</td>
                    <td style={{ color: 'var(--danger)' }}>{JSON.stringify(f.leaked_values)}</td>
                    <td><pre className="code-block">{JSON.stringify(f.received_payload, null, 2)}</pre></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
