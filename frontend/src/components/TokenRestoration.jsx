import React, { useState } from 'react';
import { restoreToken } from '../services/api';

export default function TokenRestoration({ metrics, onRefreshMetrics }) {
  const [tokenInput, setTokenInput] = useState('');
  const [sessionInput, setSessionInput] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const rest = metrics?.restoration_analytics || {};

  const handleTestRestore = async (e) => {
    e.preventDefault();
    if (!tokenInput.trim() || !sessionInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await restoreToken(tokenInput.trim(), sessionInput.trim());
      setResult(res);
      if (onRefreshMetrics) onRefreshMetrics();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
        <div className="metric-card">
          <div className="metric-label">Tokens Generated</div>
          <div className="metric-value">{rest.tokens_generated || 0}</div>
          <div className="metric-subtext">Active in Vault: {rest.active_tokens_in_vault || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Authorized Restorations</div>
          <div className="metric-value">{rest.successful_restorations || 0}</div>
          <div className="metric-subtext">Session-matched resolution</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Cross-Session Blocks</div>
          <div className="metric-value">{rest.cross_session_attempts || 0}</div>
          <div className="metric-subtext">Unauthorized session isolation</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Restoration Accuracy</div>
          <div className="metric-value">
            {rest.restoration_accuracy != null ? `${rest.restoration_accuracy}%` : '100%'}
          </div>
          <div className="metric-subtext">Authorized precision</div>
        </div>
      </div>

      <div className="grid-cols-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Token Restoration Sandbox</span>
          </div>
          <form onSubmit={handleTestRestore}>
            <div className="form-group">
              <label className="form-label">Token String:</label>
              <input
                type="text"
                className="form-control"
                placeholder="[TOK_...] or TOK_..."
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Caller Session ID:</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. session_123"
                value={sessionInput}
                onChange={(e) => setSessionInput(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Verifying...' : 'Restore Token'}
            </button>
          </form>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Vault Resolution Output</span>
          </div>
          {error && (
            <div style={{ padding: '0.65rem 0.85rem', background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', color: 'var(--danger)', borderRadius: '4px', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
              Error: {error}
            </div>
          )}
          {result ? (
            <div>
              <div style={{ marginBottom: '0.65rem' }}>
                Status:{' '}
                <span className={`badge ${result.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                  {result.status}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                <strong>Reason:</strong> {result.reason}
              </div>
              {result.value && (
                <div style={{ fontSize: '0.8rem', marginBottom: '0.65rem' }}>
                  <strong>Restored Value:</strong> <code>{result.value}</code>
                </div>
              )}
              <pre className="code-block">{JSON.stringify(result, null, 2)}</pre>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '1.25rem' }}>
              Enter a token and session ID to test token rehydration.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
