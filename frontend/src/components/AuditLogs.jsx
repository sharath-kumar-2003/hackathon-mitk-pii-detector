import React, { useState } from 'react';

const DECISION_BADGE = {
  ALLOW: 'badge-success',
  TOKENIZE: 'badge-info',
  REDACT: 'badge-warning',
  BLOCK: 'badge-danger',
  BLOCKED: 'badge-danger',
  SANITIZED: 'badge-info',
  ALLOWED: 'badge-success',
  LEAKAGE_FAILED: 'badge-danger'
};

export default function AuditLogs({ logs }) {
  const [expanded, setExpanded] = useState(null);

  if (!logs || logs.length === 0) {
    return (
      <div className="card empty-state">
        <div className="empty-title">No Audit Events Yet</div>
        <p>Audit records appear here after agent requests are processed through the firewall gateway.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Security Audit Events</span>
        <span className="badge badge-neutral">{logs.length} entries</span>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Request ID</th>
              <th>Tool</th>
              <th>Decision</th>
              <th>PII Detected</th>
              <th>Status</th>
              <th>Total ms</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, i) => (
              <React.Fragment key={i}>
                <tr>
                  <td style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    {log.timestamp_iso}
                  </td>
                  <td><code style={{ fontSize: '0.725rem' }}>{log.request_id}</code></td>
                  <td>{log.tool_name}</td>
                  <td>
                    <span className={`badge ${DECISION_BADGE[log.policy_decision] || 'badge-neutral'}`}>
                      {log.policy_decision}
                    </span>
                  </td>
                  <td>
                    {Array.isArray(log.pii_detected) && log.pii_detected.length > 0 ? (
                      <span className="badge badge-neutral">{log.pii_detected.length} entities</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>None</span>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${DECISION_BADGE[log.final_status] || 'badge-neutral'}`}>
                      {log.final_status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.725rem' }}>{log.timings_ms?.total_ms || '—'}</td>
                  <td>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '0.15rem 0.45rem', fontSize: '0.725rem' }}
                      onClick={() => setExpanded(expanded === i ? null : i)}
                    >
                      {expanded === i ? 'Hide' : 'Expand'}
                    </button>
                  </td>
                </tr>
                {expanded === i && (
                  <tr>
                    <td colSpan="8">
                      <div style={{ padding: '0.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
                        <div>
                          <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '0.2rem', color: 'var(--text-muted)' }}>POLICY REASON</div>
                          <div style={{ fontSize: '0.8rem' }}>{log.policy_reason}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '0.2rem', color: 'var(--text-muted)' }}>VERIFICATION</div>
                          <div style={{ fontSize: '0.8rem', color: log.outbound_verification?.passed ? 'var(--success)' : 'var(--danger)' }}>
                            {log.outbound_verification?.explanation || 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-muted)' }}>PII ENTITIES &amp; ACTIONS</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            {Array.isArray(log.pii_detected) && log.pii_detected.length > 0 ? (
                              log.pii_detected.map((p, k) => {
                                const entityType = typeof p === 'string' ? p : p.entity_type;
                                // Match against sanitization_action or per-entity action if available
                                const rawAction = (typeof p === 'object' && p.action)
                                  || log.sanitization_action
                                  || log.policy_decision
                                  || 'ALLOW';
                                const act = rawAction.toUpperCase();
                                const actionBadge = {
                                  TOKENIZE: { cls: 'badge-info', label: 'TOKENIZE' },
                                  REDACT: { cls: 'badge-warning', label: 'REDACT' },
                                  ALLOW: { cls: 'badge-success', label: 'ALLOW' },
                                  BLOCK: { cls: 'badge-danger', label: 'BLOCK' },
                                }[act] || { cls: 'badge-neutral', label: act };
                                return (
                                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem' }}>
                                    <span className="badge badge-neutral">{entityType}</span>
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>→</span>
                                    <span className={`badge ${actionBadge.cls}`}>{actionBadge.label}</span>
                                  </div>
                                );
                              })
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>None</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '0.2rem', color: 'var(--text-muted)' }}>STAGE TIMINGS</div>
                          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                            policy={log.timings_ms?.policy_ms}ms | detect={log.timings_ms?.detection_ms}ms | transform={log.timings_ms?.transformation_ms}ms | verify={log.timings_ms?.verification_ms}ms
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
