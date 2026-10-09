import React from 'react';

export default function PolicyRegistry({ policies }) {
  if (!policies || policies.length === 0) {
    return (
      <div className="card empty-state">
        <div className="empty-title">No Policies Loaded</div>
        <p>Policy rules are loaded from <code>data/synthetic_tool_policies.json</code>.</p>
      </div>
    );
  }

  const actionStyle = { allow: 'badge-success', tokenize: 'badge-info', redact: 'badge-warning' };

  return (
    <div>
      {policies.map((policy, i) => (
        <div className="card" key={i}>
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <code style={{ fontWeight: 600, fontSize: '0.9rem' }}>{policy.tool_name}</code>
              <span className={`badge ${actionStyle[policy.action] || 'badge-neutral'}`}>
                {policy.action?.toUpperCase()}
              </span>
            </div>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.85rem' }}>
            {policy.description}
          </p>
          <div className="grid-cols-3">
            <div>
              <div style={{ fontSize: '0.725rem', fontWeight: 500, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Permitted Fields
              </div>
              {(policy.permitted_fields || []).map((f, j) => (
                <span key={j} className="badge badge-neutral" style={{ marginRight: '0.25rem', marginBottom: '0.25rem' }}>
                  {f}
                </span>
              ))}
            </div>
            <div>
              <div style={{ fontSize: '0.725rem', fontWeight: 500, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Protected Fields
              </div>
              {(policy.redact_pii_in || []).length === 0 ? (
                <span className="badge badge-neutral">None</span>
              ) : (
                (policy.redact_pii_in || []).map((f, j) => (
                  <span key={j} className="badge badge-warning" style={{ marginRight: '0.25rem', marginBottom: '0.25rem' }}>
                    {f}
                  </span>
                ))
              )}
            </div>
            <div>
              <div style={{ fontSize: '0.725rem', fontWeight: 500, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Enforcement
              </div>
              <span className={`badge ${policy.block_if_unpermitted_field ? 'badge-danger' : 'badge-neutral'}`}>
                {policy.block_if_unpermitted_field ? 'Block Unpermitted' : 'Permissive'}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
