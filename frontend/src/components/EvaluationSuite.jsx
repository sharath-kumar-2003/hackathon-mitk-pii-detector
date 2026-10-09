import React from 'react';
import { getExportUrl } from '../services/api';

export default function EvaluationSuite({ metrics, onRunEval, onResetData, loadingEval, loadingReset }) {
  const det = metrics?.detection_analytics || {};
  const leak = metrics?.leakage_prevention || {};
  const rest = metrics?.restoration_analytics || {};
  const perf = metrics?.performance_analytics || {};
  const testCases = det.test_cases || [];
  const hasResults = !!metrics?.total_requests;

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Evaluation Control Panel</span>
        </div>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.8rem' }}>
          Executes the labeled synthetic test suite through the security gateway. Detection accuracy, leakage
          checks, restoration validation, and timing metrics are measured from live runs.
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={onRunEval} disabled={loadingEval}>
            {loadingEval ? 'Running Test Cases...' : 'Run Benchmark'}
          </button>
          {hasResults && (
            <>
              <a href={getExportUrl('json')} target="_blank" rel="noreferrer" className="btn btn-secondary">
                Download JSON
              </a>
              <a href={getExportUrl('csv')} target="_blank" rel="noreferrer" className="btn btn-secondary">
                Download CSV
              </a>
            </>
          )}
          <button className="btn btn-danger" onClick={onResetData} disabled={loadingReset}>
            {loadingReset ? 'Resetting...' : 'Reset Data'}
          </button>
        </div>
      </div>

      {!hasResults ? (
        <div className="card empty-state">
          <div className="empty-title">Not Evaluated</div>
          <p>Click "Run Benchmark" above to compute live evaluation metrics.</p>
        </div>
      ) : (
        <div>
          <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
            <div className="metric-card">
              <div className="metric-label">F1 Score</div>
              <div className="metric-value">{det.f1_score || 'N/A'}</div>
              <div className="metric-subtext">Detection quality</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Prevention Rate</div>
              <div className="metric-value">
                {leak.leakage_prevention_rate_pct != null ? `${leak.leakage_prevention_rate_pct}%` : '100%'}
              </div>
              <div className="metric-subtext">{leak.leakage_count || 0} breaches</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Restoration Accuracy</div>
              <div className="metric-value">
                {rest.restoration_accuracy != null ? `${rest.restoration_accuracy}%` : 'N/A'}
              </div>
              <div className="metric-subtext">{rest.cross_session_attempts || 0} unauthorized blocks</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">p95 Latency</div>
              <div className="metric-value">{perf.p95_protected_ms || 0} ms</div>
              <div className="metric-subtext">+{perf.avg_added_ms || 0} ms overhead</div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Test Case Results</span>
              <span className="badge badge-neutral">{testCases.length} cases</span>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Category</th>
                    <th>Tool</th>
                    <th>Expected PII</th>
                    <th>Detected PII</th>
                    <th>Expected</th>
                    <th>Decision</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {testCases.map((tc, i) => (
                    <tr key={i}>
                      <td><code style={{ fontSize: '0.725rem' }}>{tc.id}</code></td>
                      <td style={{ fontSize: '0.75rem' }}>{tc.category}</td>
                      <td>{tc.tool_name}</td>
                      <td>{tc.expected_pii_count}</td>
                      <td>{tc.detected_pii_count}</td>
                      <td><span className="badge badge-neutral">{tc.expected_action}</span></td>
                      <td><span className={`badge ${tc.actual_decision === 'BLOCK' ? 'badge-danger' : tc.actual_decision === 'ALLOW' ? 'badge-success' : 'badge-info'}`}>{tc.actual_decision}</span></td>
                      <td>
                        <span className={`badge ${tc.passed ? 'badge-success' : 'badge-danger'}`}>
                          {tc.passed ? 'Pass' : 'Fail'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
