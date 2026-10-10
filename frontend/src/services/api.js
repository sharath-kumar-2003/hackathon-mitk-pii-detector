const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function parseError(res, defaultMsg) {
  try {
    const errorData = await res.json();
    if (typeof errorData.detail === 'string') return errorData.detail;
    if (Array.isArray(errorData.detail)) return errorData.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
    if (errorData.message) return errorData.message;
    if (errorData.error) return errorData.error;
  } catch (e) {
    // Ignore JSON parsing failure
  }
  return `${defaultMsg} (${res.status} ${res.statusText})`;
}

async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    return res;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Backend server is unreachable. Please ensure the backend is running on http://localhost:8000.');
    }
    throw err;
  }
}

export async function fetchHealth() {
  const res = await safeFetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(await parseError(res, 'Health check failed'));
  return res.json();
}

export async function fetchMetrics() {
  const res = await safeFetch(`${API_BASE}/dashboard/metrics`);
  if (!res.ok) throw new Error(await parseError(res, 'Failed to fetch metrics'));
  return res.json();
}

export async function fetchLogs(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE}/dashboard/logs${query ? `?${query}` : ''}`;
  const res = await safeFetch(url);
  if (!res.ok) throw new Error(await parseError(res, 'Failed to fetch logs'));
  return res.json();
}

export async function fetchPolicies() {
  const res = await safeFetch(`${API_BASE}/dashboard/policies`);
  if (!res.ok) throw new Error(await parseError(res, 'Failed to fetch policies'));
  return res.json();
}

export async function runAgentRequest(userRequest, sessionId, actionOverride = null) {
  const res = await safeFetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_request: userRequest, session_id: sessionId, action_override: actionOverride })
  });
  if (!res.ok) {
    throw new Error(await parseError(res, 'Agent execution failed'));
  }
  return res.json();
}

export async function runDirectGatewayRequest(toolName, argumentsObj, sessionId, actionOverride = null) {
  const res = await safeFetch(`${API_BASE}/gateway/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_name: toolName, arguments: argumentsObj, session_id: sessionId, action_override: actionOverride })
  });
  if (!res.ok) {
    throw new Error(await parseError(res, 'Direct tool invocation failed'));
  }
  return res.json();
}

export async function restoreToken(token, sessionId) {
  const res = await safeFetch(`${API_BASE}/restoration/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, session_id: sessionId })
  });
  if (!res.ok) {
    throw new Error(await parseError(res, 'Token restoration failed'));
  }
  return res.json();
}

export async function runEvaluationBenchmark() {
  const res = await safeFetch(`${API_BASE}/evaluation/run`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(await parseError(res, 'Evaluation benchmark failed'));
  }
  return res.json();
}

export async function resetEvaluationData() {
  const res = await safeFetch(`${API_BASE}/evaluation/reset`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(await parseError(res, 'Data reset failed'));
  }
  return res.json();
}

export function getExportUrl(format = 'json') {
  return `${API_BASE}/evaluation/export?format=${format}`;
}
