import React from 'react';

export default function Navbar({ activeTab, setActiveTab, logsCount, policiesCount }) {
  const tabs = [
    { id: 'sandbox', label: '🧪 Test Lab', icon: '🧪' },
    { id: 'overview', label: '📊 Overview', icon: '📊' },
    { id: 'detection', label: '🔍 Detection', icon: '🔍' },
    { id: 'leakage', label: '🔒 Leakage Prevention', icon: '🔒' },
    { id: 'restoration', label: '🔐 Token Vault', icon: '🔐' },
    { id: 'performance', label: '⚡ Performance', icon: '⚡' },
    { id: 'logs', label: `📋 Audit Logs (${logsCount})`, icon: '📋' },
    { id: 'policies', label: `📜 Policy Rules (${policiesCount})`, icon: '📜' },
    { id: 'evaluation', label: '🎯 Benchmark Suite', icon: '🎯' }
  ];

  return (
    <nav className="navbar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => setActiveTab(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
