import React from 'react';
import { getExportUrl } from '../services/api';

export default function Header({ onRunEval, onResetData, loadingEval, loadingReset, hasMetrics }) {
  return (
    <header className="top-header">
      <div className="header-brand">
        <span className="brand-icon">🛡️</span>
        <div className="header-title">
          <h1>
            PII Firewall <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', background: 'rgba(56,189,248,0.12)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(56,189,248,0.3)' }}>AI GATEWAY v2.0</span>
          </h1>
          <p>Zero-Trust Security & Reversible Tokenization Layer for AI Agents</p>
        </div>
      </div>

      <div className="header-actions">
        <div className="pulse-indicator">
          <span className="pulse-dot"></span>
          <span>Firewall Active</span>
        </div>

        {hasMetrics && (
          <>
            <a
              href={getExportUrl('json')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
              title="Download full JSON metrics report"
            >
              📥 JSON
            </a>
            <a
              href={getExportUrl('csv')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
              title="Download CSV breakdown report"
            >
              📊 CSV
            </a>
          </>
        )}
        <button className="btn btn-primary" onClick={onRunEval} disabled={loadingEval}>
          {loadingEval ? '⚡ Running Evaluation...' : '⚡ Run Benchmark'}
        </button>
        <button className="btn btn-danger" onClick={onResetData} disabled={loadingReset}>
          {loadingReset ? '⏳ Resetting...' : '🗑️ Reset Data'}
        </button>
      </div>
    </header>
  );
}

