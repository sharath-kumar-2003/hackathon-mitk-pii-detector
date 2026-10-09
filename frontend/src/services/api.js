const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/dashboard/metrics`);
  return res.json();
}

export async function fetchLogs(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE}/dashboard/logs${query ? `?${query}` : ''}`;
  const res = await fetch(url);
  return res.json();
}

export async function fetchPolicies() {
  const res = await fetch(`${API_BASE}/dashboard/policies`);
  return res.json();
}

export async function runAgentRequest(userRequest, sessionId) {
  const res = await fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_request: userRequest, session_id: sessionId })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(errorData.detail || 'Request failed');
  }
  return res.json();
}

export async function runDirectGatewayRequest(toolName, argumentsObj, sessionId) {
  const res = await fetch(`${API_BASE}/gateway/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_name: toolName, arguments: argumentsObj, session_id: sessionId })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Direct invocation failed' }));
    throw new Error(errorData.detail || 'Direct invocation failed');
  }
  return res.json();
}

export async function restoreToken(token, sessionId) {
  const res = await fetch(`${API_BASE}/restoration/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, session_id: sessionId })
  });
  if (!res.ok) {
    throw new Error('Restoration failed');
  }
  return res.json();
}

export async function runEvaluationBenchmark() {
  const res = await fetch(`${API_BASE}/evaluation/run`, { method: 'POST' });
  if (!res.ok) {
    throw new Error('Evaluation benchmark failed');
  }
  return res.json();
}

export async function resetEvaluationData() {
  const res = await fetch(`${API_BASE}/evaluation/reset`, { method: 'POST' });
  if (!res.ok) {
    throw new Error('Data reset failed');
  }
  return res.json();
}

export function getExportUrl(format = 'json') {
  return `${API_BASE}/evaluation/export?format=${format}`;
}
