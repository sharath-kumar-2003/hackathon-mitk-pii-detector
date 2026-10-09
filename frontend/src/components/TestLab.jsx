import React, { useState } from 'react';
import { runAgentRequest, runDirectGatewayRequest } from '../services/api';

const SAMPLE_PROMPTS = [
  { label: 'Email + Tokenization', value: 'Send email to test.account@example.com with body containing phone 9000000001 and Aadhaar 1234 5678 9012' },
  { label: 'Web Search Redaction', value: 'Search for patient John Doe SSN 123-45-6789 on web_search' },
  { label: 'Audit Tool + PAN', value: 'Create audit report with PAN ABCDE1234F for user Ravi Kumar, Aadhaar 9876 5432 1098' },
  { label: 'Customer Lookup', value: 'Customer lookup for cust_1001 with fields status, email' },
  { label: 'Full Onboarding Profile', value: "Process the customer onboarding profile for John Michael Doe (SSN: 123-45-6789, DOB: 1985-04-12, Driver's License: DL-987654321, Passport No: A12345678, Tax ID/PAN: ABCDE1234F, Personal Email: john.doe@personal.com, Work Email: j.doe@enterprise.io, Mobile: +1-555-019-2834, Home Landline: +1-555-019-8765, Residential Address: 742 Evergreen Terrace, Springfield, IL 62704, Credit Card: 4532-xxxx-xxxx-8891 expiring 08/28 with CVV 492, Bank Account: 9876543210 routing 021000021)" },
];

const DIRECT_TOOLS = ['web_search', 'send_email', 'customer_lookup', 'internal_audit_tool', 'document_summarizer'];

const ACTION_META = {
  redact:   { bg: '#3d1f1f', border: '#8b2020', text: '#f87171', label: 'REDACT' },
  tokenize: { bg: '#1a2a3d', border: '#1e4db7', text: '#60a5fa', label: 'TOKENIZE' },
  allow:    { bg: '#1a2d1a', border: '#16a34a', text: '#4ade80', label: 'ALLOW' },
  block:    { bg: '#2d1a1a', border: '#b91c1c', text: '#ef4444', label: 'BLOCK' },
};

function ActionBadge({ action, decision }) {
  const key = (action || decision || '').toLowerCase();
  const m = ACTION_META[key] || { bg: '#1a1a2e', border: '#444', text: '#aaa', label: (decision || action || '').toUpperCase() };
  return (
    <span style={{
      background: m.bg, border: `1px solid ${m.border}`, color: m.text,
      borderRadius: '4px', padding: '2px 8px', fontSize: '0.7rem', fontWeight: 700,
      letterSpacing: '0.04em', display: 'inline-block',
    }}>{m.label}</span>
  );
}

function DecisionBadge({ decision }) {
  const map = {
    BLOCK: 'badge-danger', BLOCKED: 'badge-danger',
    TOKENIZE: 'badge-info', REDACT: 'badge-warning',
    ALLOW: 'badge-success', ALLOWED: 'badge-success',
  };
  return <span className={`badge ${map[decision] || 'badge-neutral'}`}>{decision}</span>;
}

/** Original text: highlights PII values in red */
function HighlightedOriginal({ text, piiEntities }) {
  if (!text || typeof text !== 'string') return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>;
  if (!piiEntities || piiEntities.length === 0) {
    return <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>{text}</span>;
  }

  const intervals = [];
  for (const entity of piiEntities) {
    const val = entity.value;
    if (!val) continue;
    let idx = 0;
    while (true) {
      const pos = text.toLowerCase().indexOf(val.toLowerCase(), idx);
      if (pos === -1) break;
      intervals.push({ start: pos, end: pos + val.length, type: entity.entity_type });
      idx = pos + 1;
    }
  }

  if (intervals.length === 0) {
    return <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>{text}</span>;
  }

  const sorted = intervals.sort((a, b) => a.start - b.start);
  const merged = [{ ...sorted[0] }];
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1];
    if (sorted[i].start <= last.end) {
      last.end = Math.max(last.end, sorted[i].end);
    } else {
      merged.push({ ...sorted[i] });
    }
  }

  const parts = [];
  let cursor = 0;
  for (const seg of merged) {
    if (cursor < seg.start) parts.push({ text: text.slice(cursor, seg.start), pii: false });
    parts.push({ text: text.slice(seg.start, seg.end), pii: true, type: seg.type });
    cursor = seg.end;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), pii: false });

  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
      {parts.map((p, i) =>
        p.pii ? (
          <mark key={i} style={{
            background: 'rgba(239,68,68,0.22)', color: '#f87171',
            borderRadius: '2px', padding: '0 2px', border: '1px solid rgba(239,68,68,0.4)',
          }} title={p.type}>{p.text}</mark>
        ) : (
          <span key={i} style={{ color: 'var(--text-secondary)' }}>{p.text}</span>
        )
      )}
    </span>
  );
}

/** Sanitized text: highlights <ENTITY_TYPE> placeholders in amber (redact) or TOK_ tokens in blue (tokenize) */
function SanitizedOutput({ action, text }) {
  if (!text) return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>;
  const str = typeof text === 'string' ? text : JSON.stringify(text, null, 2);

  if (action === 'redact') {
    const parts = str.split(/(\[REDACTED_[A-Z_]+\])/g);
    return (
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {parts.map((p, i) =>
          /^\[REDACTED_[A-Z_]+\]$/.test(p) ? (
            <mark key={i} style={{
              background: 'rgba(251,191,36,0.2)', color: '#fbbf24',
              borderRadius: '3px', padding: '0 4px', border: '1px solid rgba(251,191,36,0.45)',
              fontWeight: 700, fontSize: '0.72rem',
            }}>{p}</mark>
          ) : (
            <span key={i} style={{ color: 'var(--text-secondary)' }}>{p}</span>
          )
        )}
      </span>
    );
  }

  if (action === 'tokenize') {
    const parts = str.split(/(<[A-Z0-9_]+>)/g);
    return (
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {parts.map((p, i) =>
          /^<[A-Z0-9_]+>$/.test(p) ? (
            <mark key={i} style={{
              background: 'rgba(96,165,250,0.15)', color: '#60a5fa',
              borderRadius: '3px', padding: '0 4px', border: '1px solid rgba(96,165,250,0.35)',
              fontWeight: 700, fontSize: '0.72rem',
            }}>{p}</mark>
          ) : (
            <span key={i} style={{ color: 'var(--text-secondary)' }}>{p}</span>
          )
        )}
      </span>
    );
  }

  return <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)' }}>{str}</span>;
}

export default function TestLab({ onRefreshAll }) {
  const [mode, setMode] = useState('agent');
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0].value);
  const [sessionId, setSessionId] = useState('session_' + Math.random().toString(36).substr(2, 6));
  const [directTool, setDirectTool] = useState('document_summarizer');
  const [directArgs, setDirectArgs] = useState(JSON.stringify({
    title: "Q3 Financial Report",
    content: "This report was prepared by John Michael Doe (SSN: 123-45-6789, Email: john.doe@enterprise.io, Phone: +1-555-019-2834). Account: 9876543210, routing 021000021.",
  }, null, 2));
  const [protectionMode, setProtectionMode] = useState('');
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
        res = await runAgentRequest(prompt, sessionId, protectionMode || null);
      } else {
        const args = JSON.parse(directArgs);
        res = await runDirectGatewayRequest(directTool, args, sessionId, protectionMode || null);
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
  const piiDetected = gw?.pii_detected || [];
  const action = gw?.action?.toLowerCase() || '';
  const originalArgs = result?.tool_request?.arguments
    || (mode === 'direct' ? (() => { try { return JSON.parse(directArgs); } catch { return null; } })() : null);
  const originalStr = originalArgs ? JSON.stringify(originalArgs, null, 2) : null;

  return (
    <div>
      {/* ── Input Card ───────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Security Gateway — Interactive Test Lab</span>
          <span className="badge badge-success">Firewall Active</span>
        </div>

        <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '0.85rem' }}>
          <button className={`btn ${mode === 'agent' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('agent')}>
            Agent Simulation
          </button>
          <button className={`btn ${mode === 'direct' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('direct')}>
            Direct Gateway Call
          </button>
        </div>

        <form onSubmit={handleRun}>
          {mode === 'agent' ? (
            <div className="form-group">
              <label className="form-label">Natural Language Prompt:</label>
              <textarea className="form-control" rows={3} value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="E.g. Send email to user@example.com with Aadhaar 1234 5678 9012" />
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Target Tool:</label>
                <select className="form-control" value={directTool} onChange={(e) => setDirectTool(e.target.value)}>
                  {DIRECT_TOOLS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">JSON Arguments:</label>
                <textarea className="form-control" rows={6} value={directArgs}
                  onChange={(e) => setDirectArgs(e.target.value)}
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }} />
              </div>
            </>
          )}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Protection Mode:</label>
              <select className="form-control" value={protectionMode} onChange={(e) => setProtectionMode(e.target.value)}>
                <option value="">(Default Policy)</option>
                <option value="redact">Redact (Irreversible)</option>
                <option value="tokenize">Tokenize (Reversible)</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Session ID:</label>
              <input className="form-control" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
            </div>
            <div style={{ marginTop: '1.25rem' }}>
              <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? '⏳ Processing...' : '▶ Execute Pipeline'}
              </button>
            </div>
          </div>
        </form>

        {mode === 'agent' && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '0.25rem' }}>Presets:</span>
            {SAMPLE_PROMPTS.map((s, i) => (
              <button key={i} className="btn btn-secondary"
                style={{ fontSize: '0.725rem', padding: '0.25rem 0.5rem' }}
                onClick={() => setPrompt(s.value)}>{s.label}</button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger-border)', backgroundColor: 'var(--danger-bg)' }}>
          <div style={{ color: 'var(--danger)', fontWeight: 500, fontSize: '0.825rem' }}>⚠ Error: {error}</div>
        </div>
      )}

      {result && gw && (
        <div>
          {/* ── Summary Metrics ─────────────────────── */}
          <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
            <div className="metric-card">
              <div className="metric-label">Request ID</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', fontWeight: 600 }}>{gw.request_id}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Firewall Action</div>
              <ActionBadge action={action} decision={gw.decision} />
            </div>
            <div className="metric-card">
              <div className="metric-label">PII Detected</div>
              <div className="metric-value" style={{ color: piiDetected.length > 0 ? '#f87171' : '#4ade80' }}>
                {piiDetected.length}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Leakage Check</div>
              <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                {gw.outbound_verification?.passed ? '✓ Passed' : '✗ Breach'}
              </span>
            </div>
          </div>

          {/* ── Redaction / Tokenization Visualizer ─── */}
          {piiDetected.length > 0 && (action === 'redact' || action === 'tokenize') && (
            <div className="card" style={{
              border: `1px solid ${action === 'redact' ? 'rgba(139,32,32,0.6)' : 'rgba(30,77,183,0.55)'}`,
              background: action === 'redact' ? 'rgba(61,31,31,0.2)' : 'rgba(26,42,61,0.2)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.1rem' }}>{action === 'redact' ? '🛡️' : '🔐'}</span>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    {action === 'redact' ? 'Redaction Applied' : 'Tokenization Applied'}
                  </span>
                  <ActionBadge action={action} />
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {piiDetected.length} PII field{piiDetected.length !== 1 ? 's' : ''} protected
                </span>
              </div>

              {/* Side-by-side diff */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f87171', marginBottom: '0.4rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                    ⚠ Original — PII Exposed
                  </div>
                  <div style={{ background: 'var(--bg-code)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(239,68,68,0.25)', minHeight: '80px' }}>
                    <HighlightedOriginal text={originalStr} piiEntities={piiDetected} />
                  </div>
                  <div style={{ marginTop: '0.4rem', display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {[...new Set(piiDetected.map(p => p.entity_type))].map((t, i) => (
                      <span key={i} style={{
                        background: 'rgba(239,68,68,0.12)', color: '#f87171',
                        border: '1px solid rgba(239,68,68,0.3)', borderRadius: '3px',
                        padding: '1px 6px', fontSize: '0.67rem', fontWeight: 600,
                      }}>{t}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <div style={{
                    fontSize: '0.7rem', fontWeight: 700,
                    color: action === 'redact' ? '#fbbf24' : '#60a5fa',
                    marginBottom: '0.4rem', letterSpacing: '0.04em', textTransform: 'uppercase',
                  }}>
                    ✓ {action === 'redact' ? 'After Redaction — Safe' : 'After Tokenization — Safe'}
                  </div>
                  <div style={{
                    background: 'var(--bg-code)', borderRadius: '6px', padding: '0.75rem',
                    border: `1px solid ${action === 'redact' ? 'rgba(251,191,36,0.25)' : 'rgba(96,165,250,0.25)'}`,
                    minHeight: '80px',
                  }}>
                    <SanitizedOutput action={action} text={gw.sanitized_arguments} />
                  </div>
                  <div style={{ marginTop: '0.4rem', fontSize: '0.71rem', color: 'var(--text-muted)' }}>
                    {action === 'redact'
                      ? '🟡 PII replaced with <ENTITY_TYPE> placeholders — irreversible'
                      : '🔵 PII replaced with reversible tokens — restorable by authorized system'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Block / Allow banner ─────────────────── */}
          {(action === 'block' || (action !== 'redact' && action !== 'tokenize')) && (
            <div className="card" style={{
              border: `1px solid ${action === 'block' ? 'rgba(185,28,28,0.5)' : 'rgba(22,163,74,0.4)'}`,
              background: action === 'block' ? 'rgba(45,26,26,0.3)' : 'rgba(26,45,26,0.3)',
              display: 'flex', alignItems: 'center', gap: '0.75rem',
            }}>
              <span style={{ fontSize: '1.4rem' }}>{action === 'block' ? '🚫' : '✅'}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                  {action === 'block' ? 'Request Blocked by Policy' : piiDetected.length === 0 ? 'No PII Detected — Passed Through' : 'Allowed'}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{gw.reason}</div>
              </div>
            </div>
          )}

          {/* ── Pipeline Steps ───────────────────────── */}
          <div className="grid-cols-2">
            {result.tool_request && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">1️⃣ Agent Tool Call (Original)</span>
                  <code style={{ fontSize: '0.75rem' }}>{result.tool_request.tool_name}</code>
                </div>
                <pre className="code-block">{JSON.stringify(result.tool_request.arguments, null, 2)}</pre>
              </div>
            )}

            <div className="card">
              <div className="card-header">
                <span className="card-title">2️⃣ Sanitized Outgoing Payload</span>
                <ActionBadge action={action} decision={gw.action?.toUpperCase?.()} />
              </div>
              <div className="code-block" style={{ minHeight: '80px' }}>
                <SanitizedOutput action={action} text={gw.sanitized_arguments} />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">3️⃣ Payload Received by Mock Tool</span>
                <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>Evidence</span>
              </div>
              <pre className="code-block">{JSON.stringify(gw.received_by_mock_tool, null, 2)}</pre>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">4️⃣ Tool Output & Restoration</span>
              </div>
              <pre className="code-block">{JSON.stringify(gw.mock_tool_output, null, 2)}</pre>
              {gw.restoration_result?.tokens_found?.length > 0 && (
                <div style={{
                  marginTop: '0.65rem', padding: '0.5rem 0.75rem',
                  background: 'rgba(96,165,250,0.1)', borderRadius: '4px',
                  border: '1px solid rgba(96,165,250,0.25)', fontSize: '0.775rem', color: '#60a5fa',
                }}>
                  🔓 <strong>Restoration:</strong> {gw.restoration_result.tokens_found.length} token(s) resolved to original values.
                </div>
              )}
            </div>
          </div>

          {/* ── PII Breakdown Table ──────────────────── */}
          {piiDetected.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">🔍 Detected PII Breakdown</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{piiDetected.length} field{piiDetected.length !== 1 ? 's' : ''}</span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Entity Type', 'Value Detected', 'Confidence', 'Action Applied'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.6rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.72rem' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {piiDetected.map((p, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                        <td style={{ padding: '0.4rem 0.6rem' }}>
                          <span style={{
                            background: 'rgba(239,68,68,0.12)', color: '#f87171',
                            border: '1px solid rgba(239,68,68,0.3)', borderRadius: '3px',
                            padding: '1px 6px', fontSize: '0.68rem', fontWeight: 600,
                          }}>{p.entity_type}</span>
                        </td>
                        <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {p.value}
                        </td>
                        <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <div style={{ width: '60px', height: '4px', background: 'var(--border-subtle)', borderRadius: '2px', overflow: 'hidden' }}>
                              <div style={{ width: `${(p.score || 0.9) * 100}%`, height: '100%', background: '#4ade80', borderRadius: '2px' }} />
                            </div>
                            <span>{Math.round((p.score || 0.9) * 100)}%</span>
                          </div>
                        </td>
                        <td style={{ padding: '0.4rem 0.6rem' }}>
                          <ActionBadge action={action} decision={action.toUpperCase()} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Leakage Verification ─────────────────── */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">🔒 Outbound Leakage Verification</span>
              <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                {gw.outbound_verification?.passed ? '✓ No Leakage' : '✗ Breach Detected'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              {gw.outbound_verification?.explanation}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
              <span>policy={Math.round(gw.timings_ms?.policy_ms || 0)}ms</span>
              <span>detection={Math.round(gw.timings_ms?.detection_ms || 0)}ms</span>
              <span>transform={Math.round(gw.timings_ms?.transformation_ms || 0)}ms</span>
              <span>verify={Math.round(gw.timings_ms?.verification_ms || 0)}ms</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>total={Math.round(gw.timings_ms?.total_ms || 0)}ms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
