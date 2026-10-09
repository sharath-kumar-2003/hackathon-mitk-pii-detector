import React, { useState } from 'react';
import { runAgentRequest, runDirectGatewayRequest } from '../services/api';

const SAMPLE_PROMPTS = [
  { label: 'Email + Tokenization', value: 'Send email to test.account@example.com with body containing phone 9000000001 and Aadhaar 1234 5678 9012' },
  { label: 'Debit Card & PIN', value: 'Debit card 4532 8912 3456 7890 with ATM PIN 4829 for customer verification' },
  { label: 'Web Search Redaction', value: 'Search customer helpline number 9876543210 on web_search' },
  { label: 'Customer Lookup', value: 'Customer lookup for cust_1001 with fields status, email' },
  { label: 'Audit Tool + PAN', value: 'Create audit report with PAN ABCDE1234F for user Ravi Kumar, Aadhaar 9876 5432 1098' },
];

const DIRECT_TOOLS = ['web_search', 'send_email', 'customer_lookup', 'internal_audit_tool'];

function DecisionBadge({ decision }) {
  const map = {
    BLOCK: 'badge-danger', BLOCKED: 'badge-danger',
    TOKENIZE: 'badge-info', REDACT: 'badge-warning',
    ALLOW: 'badge-success', ALLOWED: 'badge-success',
  };
  return <span className={`badge ${map[decision] || 'badge-neutral'}`}>{decision}</span>;
}

export default function TestLab({ onRefreshAll }) {
  const [mode, setMode] = useState('agent');
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0].value);
  const [sessionId, setSessionId] = useState('session_' + Math.random().toString(36).substr(2, 6));
  const [directTool, setDirectTool] = useState('send_email');
  const [directArgs, setDirectArgs] = useState(JSON.stringify({
    to: "recipient@example.com",
    subject: "Test Notification",
    body: "Contact John Doe at phone 9876543210 or email john.doe@example.com"
  }, null, 2));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRun = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let res;
      if (mode === 'agent') {
        res = await runAgentRequest(prompt, sessionId);
      } else {
        const args = JSON.parse(directArgs);
        res = await runDirectGatewayRequest(directTool, args, sessionId);
      }
      setResult(res);
      if (onRefreshAll) onRefreshAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const gw = result?.gateway_result || result;

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Security Gateway — Interactive Test Lab</span>
          <span className="badge badge-success">Firewall Active</span>
        </div>

        <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '0.85rem' }}>
          <button
            className={`btn ${mode === 'agent' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode('agent')}
          >
            Agent Simulation
          </button>
          <button
            className={`btn ${mode === 'direct' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode('direct')}
          >
            Direct Gateway Call
          </button>
        </div>

        <form onSubmit={handleRun}>
          {mode === 'agent' ? (
            <div className="form-group">
              <label className="form-label">Natural Language Prompt:</label>
              <textarea
                className="form-control"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="E.g. Send email to user@example.com with Aadhaar 1234 5678 9012"
              />
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Target Tool:</label>
                <select
                  className="form-control"
                  value={directTool}
                  onChange={(e) => setDirectTool(e.target.value)}
                >
                  {DIRECT_TOOLS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">JSON Arguments:</label>
                <textarea
                  className="form-control"
                  rows={6}
                  value={directArgs}
                  onChange={(e) => setDirectArgs(e.target.value)}
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
                />
              </div>
            </>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Session ID:</label>
              <input
                className="form-control"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
              />
            </div>
            <div style={{ marginTop: '1.25rem' }}>
              <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? 'Processing...' : 'Execute Pipeline'}
              </button>
            </div>
          </div>
        </form>

        {mode === 'agent' && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '0.25rem' }}>Presets:</span>
            {SAMPLE_PROMPTS.map((s, i) => (
              <button
                key={i}
                className="btn btn-secondary"
                style={{ fontSize: '0.725rem', padding: '0.25rem 0.5rem' }}
                onClick={() => setPrompt(s.value)}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger-border)', backgroundColor: 'var(--danger-bg)' }}>
          <div style={{ color: 'var(--danger)', fontWeight: 500, fontSize: '0.825rem' }}>Error: {error}</div>
        </div>
      )}

      {result && gw && (
        <div>
          <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
            <div className="metric-card">
              <div className="metric-label">Request ID</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', fontWeight: 600 }}>{gw.request_id}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Firewall Decision</div>
              <DecisionBadge decision={gw.decision} />
            </div>
            <div className="metric-card">
              <div className="metric-label">PII Detected</div>
              <div className="metric-value">{gw.pii_detected?.length || 0}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Verification</div>
              <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                {gw.outbound_verification?.passed ? 'Passed' : 'Breach'}
              </span>
            </div>
          </div>

          <div className="grid-cols-2">
            {result.tool_request && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">1. Agent Tool Call (Original)</span>
                  <code style={{ fontSize: '0.75rem' }}>{result.tool_request.tool_name}</code>
                </div>
                <pre className="code-block">{JSON.stringify(result.tool_request.arguments, null, 2)}</pre>
              </div>
            )}

            <div className="card">
              <div className="card-header">
                <span className="card-title">2. Sanitized Outgoing Payload</span>
                <DecisionBadge decision={gw.action?.toUpperCase?.()} />
              </div>
              <pre className="code-block">{JSON.stringify(gw.sanitized_arguments, null, 2)}</pre>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">3. Payload Received by Mock Tool</span>
                <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>Evidence</span>
              </div>
              <pre className="code-block">{JSON.stringify(gw.received_by_mock_tool, null, 2)}</pre>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">4. Tool Output & Restoration</span>
              </div>
              <pre className="code-block">{JSON.stringify(gw.mock_tool_output, null, 2)}</pre>
              {gw.restoration_result?.tokens_found?.length > 0 && (
                <div style={{ marginTop: '0.65rem', padding: '0.5rem 0.75rem', background: 'var(--bg-subtle)', borderRadius: '4px', fontSize: '0.775rem' }}>
                  <strong>Restoration:</strong> {gw.restoration_result.tokens_found.length} token(s) resolved.
                </div>
              )}
            </div>
          </div>

          {gw.pii_detected?.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">Detected PII Categories</span></div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                {[...new Set(gw.pii_detected.map(p => p.entity_type))].map((t, i) => (
                  <span key={i} className="badge badge-neutral">{t}</span>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <div className="card-header">
              <span className="card-title">Outbound Verification Report</span>
              <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                {gw.outbound_verification?.passed ? 'Passed' : 'Breach Detected'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {gw.outbound_verification?.explanation}
            </div>
            <div style={{ marginTop: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
              Timings: policy={gw.timings_ms?.policy_ms}ms | detection={gw.timings_ms?.detection_ms}ms | transform={gw.timings_ms?.transformation_ms}ms | verify={gw.timings_ms?.verification_ms}ms | total={gw.timings_ms?.total_ms}ms
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
