import React from 'react';
import { getExportUrl } from '../services/api';

export default function Header({ onRunEval, onResetData, loadingEval, loadingReset, hasMetrics }) {
  return (
    <header className="top-header">
      <div className="header-brand">
        <div className="header-title">
          <h1>PII Firewall for AI Agents</h1>
          <p>Cybersecurity Gateway & Reversible Tokenization Layer</p>
        </div>
      </div>
      <div className="header-actions">
        {hasMetrics && (
          <>
            <a
              href={getExportUrl('json')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
            >
              Export JSON
            </a>
            <a
              href={getExportUrl('csv')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
            >
              Export CSV
            </a>
          </>
        )}
        <button className="btn btn-primary" onClick={onRunEval} disabled={loadingEval}>
          {loadingEval ? 'Running Evaluation...' : 'Run Benchmark'}
        </button>
        <button className="btn btn-danger" onClick={onResetData} disabled={loadingReset}>
          {loadingReset ? 'Resetting...' : 'Reset'}
        </button>
      </div>
    </header>
  );
}
