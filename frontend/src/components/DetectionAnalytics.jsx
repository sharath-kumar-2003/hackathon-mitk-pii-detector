import React from 'react';

export default function DetectionAnalytics({ metrics }) {
  if (!metrics || !metrics.detection_analytics) {
    return (
      <div className="card empty-state">
        <div className="empty-title">No Detection Analytics Available</div>
        <p>Run the evaluation benchmark to calculate precision, recall, F1, and category breakdowns.</p>
      </div>
    );
  }

  const det = metrics.detection_analytics;
  const categories = det.by_category || {};

  return (
    <div>
      <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
        <div className="metric-card">
          <div className="metric-label">Precision</div>
          <div className="metric-value">{det.precision != null ? det.precision : 'N/A'}</div>
          <div className="metric-subtext">TP / (TP + FP)</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Recall</div>
          <div className="metric-value">{det.recall != null ? `${(det.recall * 100).toFixed(1)}%` : 'N/A'}</div>
          <div className="metric-subtext">TP / (TP + FN)</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">F1 Score</div>
          <div className="metric-value">
            {det.f1_score != null ? det.f1_score : 'N/A'}
          </div>
          <div className="metric-subtext">Harmonic Mean</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">True Positives (TP)</div>
          <div className="metric-value">
            {det.tp || 0}
          </div>
          <div className="metric-subtext">FP: {det.fp || 0} | FN: {det.fn || 0}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">PII Category Detection Breakdown</span>
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Test Cases</th>
                <th>Expected</th>
                <th>Detected</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(categories).length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No category data recorded</td>
                </tr>
              ) : (
                Object.entries(categories).map(([cat, info]) => (
                  <tr key={cat}>
                    <td><code>{cat}</code></td>
                    <td>{info.cases}</td>
                    <td>{info.expected}</td>
                    <td>{info.detected}</td>
                    <td>
                      <span className={`badge ${info.detected >= info.expected ? 'badge-success' : 'badge-neutral'}`}>
                        {info.detected >= info.expected ? 'Optimal' : 'Partial'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
