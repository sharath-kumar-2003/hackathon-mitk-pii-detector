import React, { useState } from 'react';
import { runAgentRequest, runDirectGatewayRequest } from '../services/api';

const SAMPLE_PROMPTS = [
  { label: 'Email + Tokenization', value: 'Send email to test.account@example.com with body containing phone 9000000001 and Aadhaar 1234 5678 9012' },
  { label: 'Web Search Redaction', value: 'Search for patient John Doe SSN 123-45-6789 on web_search' },
  { label: 'Audit Tool + PAN', value: 'Create audit report with PAN ABCDE1234F for user Ravi Kumar, Aadhaar 9876 5432 1098' },
  { label: 'Customer Lookup', value: 'Customer lookup for cust_1001 with fields status, email' },
  { label: 'Full Onboarding Profile', value: "Process the customer onboarding profile for John Michael Doe (SSN: 123-45-6789, DOB: 1985-04-12, Driver's License: DL-987654321, Passport No: A12345678, Tax ID/PAN: ABCDE1234F, Personal Email: john.doe@personal.com, Work Email: j.doe@enterprise.io, Mobile: +1-555-019-2834, Home Landline: +1-555-019-8765, Residential Address: 742 Evergreen Terrace, Springfield, IL 62704, Credit Card: 4532-xxxx-xxxx-8891 expiring 08/28 with CVV 492, Bank Account: 9876543210 routing 021000021)" },
  { label: '🚫 Block: Unknown Tool', value: 'Use the payment_gateway tool to transfer $5000 to account 9876543210, routing 021000021, for John Doe SSN 123-45-6789', _block: true },
  { label: '🚫 Block: Unpermitted Field', value: 'Send email with extra hidden_data field containing SSN 123-45-6789 and card 4532015112830366', _block: true },
];

const DIRECT_TOOLS = ['web_search', 'send_email', 'customer_lookup', 'internal_audit_tool', 'document_summarizer'];

const DIRECT_BLOCK_PRESETS = [
  {
    label: '🚫 Unknown Tool',
    tool: 'payment_gateway',
    args: { account: '9876543210', routing: '021000021', amount: 5000, ssn: '123-45-6789' }
  },
  {
    label: '🚫 Unpermitted Field (send_email)',
    tool: 'send_email',
    args: { to: 'user@example.com', subject: 'Test', body: 'Hello', hidden_data: 'SSN: 123-45-6789', raw_pii: 'card: 4532015112830366' }
  },
  {
    label: '🚫 Unpermitted Field (web_search)',
    tool: 'web_search',
    args: { query: 'search term', user_id: 'usr_123', raw_ssn: '123-45-6789' }
  },
];

function ActionBadge({ action, decision }) {
  const key = (action || decision || '').toLowerCase();
  const map = {
    block: 'badge-danger',
    redact: 'badge-warning',
    tokenize: 'badge-info',
    allow: 'badge-success',
  };
  const cls = map[key] || 'badge-neutral';
  return <span className={`badge ${cls}`}>{(decision || action || '').toUpperCase()}</span>;
}

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
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
      {parts.map((p, i) =>
        p.pii ? (
          <mark key={i} style={{
            background: 'rgba(244,63,94,0.15)', color: '#f43f5e',
            borderRadius: '2px', padding: '0 3px', border: '1px solid rgba(244,63,94,0.3)',
          }} title={p.type}>{p.text}</mark>
        ) : (
          <span key={i} style={{ color: 'var(--text-secondary)' }}>{p.text}</span>
        )
      )}
    </span>
  );
}

// Highlights both [REDACTED_*] (amber) and <TOKEN_ID> (blue) in any mix
function SanitizedOutput({ text }) {
  if (!text) return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>;
  const str = typeof text === 'string' ? text : JSON.stringify(text, null, 2);

  // Split on BOTH redact placeholders and tokenize markers in one pass
  const parts = str.split(/(\[REDACTED_[A-Z_]+\]|<[A-Z][A-Z0-9_]*_[A-Z0-9]+>)/g);

  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
      {parts.map((p, i) => {
        if (/^\[REDACTED_[A-Z_]+\]$/.test(p)) {
          return (
            <mark key={i} style={{
              background: 'rgba(251,191,36,0.12)', color: '#fbbf24',
              borderRadius: '3px', padding: '0 4px', border: '1px solid rgba(251,191,36,0.3)',
              fontWeight: 600, fontSize: '0.72rem',
            }} title="Redacted">{p}</mark>
          );
        }
        if (/^<[A-Z][A-Z0-9_]*_[A-Z0-9]+>$/.test(p)) {
          return (
            <mark key={i} style={{
              background: 'rgba(56,189,248,0.12)', color: '#38bdf8',
              borderRadius: '3px', padding: '0 4px', border: '1px solid rgba(56,189,248,0.3)',
              fontWeight: 600, fontSize: '0.72rem',
            }} title="Tokenized">{p}</mark>
          );
        }
        return <span key={i} style={{ color: 'var(--text-secondary)' }}>{p}</span>;
      })}
    </span>
  );
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
      {/* Input Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Interactive Test Lab</span>
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
                {loading ? 'Processing...' : 'Run Pipeline'}
              </button>
            </div>
          </div>
        </form>

        {mode === 'agent' && (
          <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '0.25rem' }}>Presets:</span>
              {SAMPLE_PROMPTS.filter(s => !s._block).map((s, i) => (
                <button key={i} className="btn btn-secondary"
                  style={{ fontSize: '0.725rem', padding: '0.2rem 0.5rem' }}
                  onClick={() => setPrompt(s.value)}>{s.label}</button>
              ))}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: '#ef4444', alignSelf: 'center', marginRight: '0.25rem', fontWeight: 600 }}>Block Demos:</span>
              {SAMPLE_PROMPTS.filter(s => s._block).map((s, i) => (
                <button key={i} className="btn btn-secondary"
                  style={{ fontSize: '0.725rem', padding: '0.2rem 0.5rem', borderColor: 'rgba(239,68,68,0.4)', color: '#ef4444' }}
                  onClick={() => setPrompt(s.value)}>{s.label}</button>
              ))}
            </div>
          </div>
        )}
        {mode === 'direct' && (
          <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: '#ef4444', alignSelf: 'center', marginRight: '0.25rem', fontWeight: 600 }}>Block Presets:</span>
              {DIRECT_BLOCK_PRESETS.map((p, i) => (
                <button key={i} className="btn btn-secondary"
                  style={{ fontSize: '0.725rem', padding: '0.2rem 0.5rem', borderColor: 'rgba(239,68,68,0.4)', color: '#ef4444' }}
                  onClick={() => { setDirectTool(p.tool); setDirectArgs(JSON.stringify(p.args, null, 2)); }}>
                  {p.label}
                </button>
              ))}
            </div>
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
          {/* Summary Metrics */}
          <div className="grid-cols-4" style={{ marginBottom: '1.25rem' }}>
            <div className="metric-card">
              <div className="metric-label">Request ID</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', fontWeight: 600 }}>{gw.request_id}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Firewall Action</div>
              {(() => {
                const pv = gw.protected_values || [];
                if (pv.length === 0) return <div><ActionBadge action={action} decision={gw.decision} /></div>;
                const counts = pv.reduce((acc, x) => { acc[x.action] = (acc[x.action] || 0) + 1; return acc; }, {});
                const keys = Object.keys(counts);
                if (keys.length === 1) return <div><ActionBadge action={keys[0]} decision={keys[0]} /></div>;
                return (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.2rem' }}>
                    {keys.map(k => (
                      <span key={k} style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <ActionBadge action={k} decision={k} />
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>×{counts[k]}</span>
                      </span>
                    ))}
                  </div>
                );
              })()}
            </div>
            <div className="metric-card">
              <div className="metric-label">PII Detected</div>
              <div className="metric-value">
                {piiDetected.length}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Leakage Check</div>
              <div>
                <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                  {gw.outbound_verification?.passed ? 'Passed' : 'Breach Detected'}
                </span>
              </div>
            </div>
          </div>

          {/* Redaction / Tokenization Visualizer — always show when PII was detected */}
          {piiDetected.length > 0 && action !== 'block' && action !== 'allow' && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  {(() => {
                    const pv = gw.protected_values || [];
                    const actions = [...new Set(pv.map(x => x.action))];
                    if (actions.length === 1) {
                      return actions[0] === 'REDACT' ? 'Redaction Transformation'
                           : actions[0] === 'TOKENIZE' ? 'Tokenization Transformation'
                           : 'Sanitization Transformation';
                    }
                    return 'Sanitization Transformation (Mixed)';
                  })()}
                </span>
                {/* Legend */}
                <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {(gw.protected_values || []).some(x => x.action === 'REDACT') && (
                    <span style={{ fontSize: '0.68rem', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.4)', borderRadius: '3px', padding: '0.1rem 0.4rem', background: 'rgba(251,191,36,0.08)' }}>■ REDACT</span>
                  )}
                  {(gw.protected_values || []).some(x => x.action === 'TOKENIZE') && (
                    <span style={{ fontSize: '0.68rem', color: '#38bdf8', border: '1px solid rgba(56,189,248,0.4)', borderRadius: '3px', padding: '0.1rem 0.4rem', background: 'rgba(56,189,248,0.08)' }}>■ TOKENIZE</span>
                  )}
                </span>
              </div>

              {/* Side-by-side diff */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Original Payload (PII Exposed)
                  </div>
                  <div style={{ background: 'var(--bg-dark)', borderRadius: '6px', padding: '0.75rem', border: '1px solid var(--border-color)', minHeight: '80px' }}>
                    <HighlightedOriginal text={originalStr} piiEntities={piiDetected} />
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Sanitized Payload (Safe)
                  </div>
                  <div style={{ background: 'var(--bg-dark)', borderRadius: '6px', padding: '0.75rem', border: '1px solid var(--border-color)', minHeight: '80px' }}>
                    <SanitizedOutput text={gw.sanitized_arguments} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ===== BLOCKED REQUEST DISPLAY ===== */}
          {action === 'block' && (
            <div style={{ marginBottom: '1.25rem' }}>
              {/* Big blocked banner */}
              <div style={{
                background: 'rgba(239,68,68,0.06)',
                border: '2px solid rgba(239,68,68,0.4)',
                borderRadius: '10px',
                padding: '1.5rem',
                marginBottom: '1rem',
                position: 'relative',
                overflow: 'hidden'
              }}>
                {/* Background watermark */}
                <div style={{
                  position: 'absolute', right: '1.5rem', top: '50%', transform: 'translateY(-50%)',
                  fontSize: '5rem', opacity: 0.06, fontWeight: 900, color: '#ef4444', userSelect: 'none',
                  lineHeight: 1
                }}>BLOCKED</div>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', position: 'relative' }}>
                  {/* Shield icon */}
                  <div style={{
                    width: '48px', height: '48px', borderRadius: '50%',
                    background: 'rgba(239,68,68,0.12)', border: '2px solid rgba(239,68,68,0.35)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.5rem', flexShrink: 0
                  }}>🛡️</div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '1rem', fontWeight: 700, color: '#ef4444' }}>Request Blocked by Firewall Policy</span>
                      <span className="badge badge-danger">BLOCK</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '0.75rem' }}>
                      {gw.reason}
                    </div>

                    {/* Block reason breakdown */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '0.25rem 0.6rem' }}>
                        <span>🔒</span> <span>Fail-Closed Security Mode</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '0.25rem 0.6rem' }}>
                        <span>🚫</span> <span>Tool Never Reached</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '0.25rem 0.6rem' }}>
                        <span>📋</span> <span>Logged to Audit Trail</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#22c55e', background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: '4px', padding: '0.25rem 0.6rem' }}>
                        <span>✅</span> <span>Zero Data Exposure</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Pipeline visualization — blocked at gateway */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Request Interception Flow</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Policy evaluated in {Math.round(gw.timings_ms?.policy_ms || 0)}ms</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0', overflowX: 'auto', padding: '0.75rem 0' }}>
                  {[
                    { label: 'AI Agent', icon: '🤖', color: 'var(--text-primary)', bg: 'var(--bg-subtle)', status: 'sent' },
                    { label: '→', arrow: true },
                    { label: 'PII Firewall Gateway', icon: '🛡️', color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: '2px solid rgba(239,68,68,0.4)', status: 'blocked' },
                    { label: '✗', arrow: true, blocked: true },
                    { label: 'External Tool', icon: '🔧', color: 'var(--text-muted)', bg: 'rgba(0,0,0,0.03)', opacity: 0.4, status: 'never_reached' },
                  ].map((step, i) => step.arrow ? (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0 0.5rem' }}>
                      <span style={{ fontSize: step.blocked ? '1.1rem' : '1.2rem', color: step.blocked ? '#ef4444' : 'var(--text-muted)', fontWeight: 700 }}>{step.label}</span>
                      {step.blocked && <span style={{ fontSize: '0.6rem', color: '#ef4444', fontWeight: 600, marginTop: '0.15rem' }}>STOPPED</span>}
                    </div>
                  ) : (
                    <div key={i} style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem',
                      background: step.bg, border: step.border || '1px solid var(--border-subtle)',
                      borderRadius: '8px', padding: '0.6rem 1rem', minWidth: '110px', opacity: step.opacity || 1
                    }}>
                      <span style={{ fontSize: '1.4rem' }}>{step.icon}</span>
                      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: step.color, textAlign: 'center' }}>{step.label}</span>
                      {step.status === 'blocked' && <span style={{ fontSize: '0.62rem', color: '#ef4444', fontWeight: 700 }}>▼ BLOCKED HERE</span>}
                      {step.status === 'never_reached' && <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>never reached</span>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Original rejected payload */}
              {result.tool_request && (
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">Rejected Payload</span>
                    <span style={{ fontSize: '0.72rem', color: '#ef4444', fontWeight: 600 }}>Never forwarded to tool</span>
                  </div>
                  <pre className="code-block" style={{ border: '1px solid rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.03)' }}>
                    {JSON.stringify(result.tool_request.arguments, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Allow / No-PII banner (non-blocked, non-sanitized) */}
          {action !== 'block' && action !== 'redact' && action !== 'tokenize' && (
            <div className="card">
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                {piiDetected.length === 0 ? 'No PII Detected — Passed Through' : 'Allowed'}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{gw.reason}</div>
            </div>
          )}

          {/* Pipeline Steps — only shown when NOT blocked */}
          {action !== 'block' && (
          <div className="grid-cols-2">
            {result.tool_request && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">1. Agent Tool Call</span>
                  <code style={{ fontSize: '0.75rem' }}>{result.tool_request.tool_name}</code>
                </div>
                <pre className="code-block">{JSON.stringify(result.tool_request.arguments, null, 2)}</pre>
              </div>
            )}

            <div className="card">
              <div className="card-header">
                <span className="card-title">2. Sanitized Outgoing Payload</span>
                <ActionBadge action={action} decision={gw.action?.toUpperCase?.()} />
              </div>
              <div className="code-block" style={{ minHeight: '80px' }}>
                <SanitizedOutput text={gw.sanitized_arguments} />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">3. Payload Received by Mock Tool</span>
              </div>
              <pre className="code-block">{JSON.stringify(gw.received_by_mock_tool, null, 2)}</pre>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">4. Tool Output &amp; Restoration</span>
                {gw.restoration_result?.tokens_found?.length > 0 && (
                  <span className="badge badge-info">
                    {gw.restoration_result.tokens_found.length} token{gw.restoration_result.tokens_found.length !== 1 ? 's' : ''} restored
                  </span>
                )}
              </div>

              {gw.restoration_result?.tokens_found?.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {/* Left: raw output with tokens highlighted */}
                  <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Raw Output (Tokenized)
                    </div>
                    <div style={{ background: 'var(--bg-dark)', borderRadius: '6px', padding: '0.75rem', border: '1px solid var(--border-color)', minHeight: '80px' }}>
                      <SanitizedOutput text={gw.mock_tool_output} />
                    </div>
                  </div>

                  {/* Right: restored output with original values */}
                  <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span>Restored Output</span>
                      <span style={{ fontSize: '0.65rem', color: '#22c55e', border: '1px solid rgba(34,197,94,0.35)', borderRadius: '3px', padding: '0.05rem 0.35rem', background: 'rgba(34,197,94,0.07)' }}>PII Restored</span>
                    </div>
                    <div style={{ background: 'var(--bg-dark)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(34,197,94,0.25)', minHeight: '80px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        {typeof gw.restoration_result.restored_text === 'string'
                          ? gw.restoration_result.restored_text
                          : JSON.stringify(gw.restoration_result.restored_text, null, 2)}
                      </span>
                    </div>

                    {/* Token → Value mapping */}
                    <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      {gw.restoration_result.restoration_details?.filter(d => d.status === 'success').map((d, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem' }}>
                          <span style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.25)', borderRadius: '3px', padding: '0.05rem 0.3rem' }}>
                            {d.token}
                          </span>
                          <span style={{ color: 'var(--text-muted)' }}>→</span>
                          <span style={{ color: '#22c55e', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                            {d.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <pre className="code-block">{JSON.stringify(gw.mock_tool_output, null, 2)}</pre>
              )}
            </div>
          </div>
          )} {/* end pipeline steps */}
          {piiDetected.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Detected PII Breakdown</span>
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
                    {piiDetected.map((p, i) => {
                      const protectedValues = gw.protected_values || [];
                      const match = protectedValues.find(pv =>
                        pv.value === p.value ||
                        (p.value && pv.value && pv.value.toLowerCase() === p.value.toLowerCase())
                      );
                      const entityAction = match?.action || action.toUpperCase() || 'ALLOW';
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '0.4rem 0.6rem' }}>
                            <span className="badge badge-neutral">{p.entity_type}</span>
                          </td>
                          <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {p.value}
                          </td>
                          <td style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}>
                            {Math.round((p.score || 0.9) * 100)}%
                          </td>
                          <td style={{ padding: '0.4rem 0.6rem' }}>
                            <ActionBadge action={entityAction} decision={entityAction} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Leakage Verification */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Outbound Leakage Verification</span>
              <span className={`badge ${gw.outbound_verification?.passed ? 'badge-success' : 'badge-danger'}`}>
                {gw.outbound_verification?.passed ? 'Passed' : 'Breach Detected'}
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
