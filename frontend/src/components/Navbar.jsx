import React from 'react';

export default function Navbar({ activeTab, setActiveTab, logsCount, policiesCount }) {
  const tabs = [
    { id: 'sandbox', label: 'Test Lab' },
    { id: 'overview', label: 'Overview' },
    { id: 'detection', label: 'Detection Analytics' },
    { id: 'leakage', label: 'Leakage Prevention' },
    { id: 'restoration', label: 'Token Restoration' },
    { id: 'performance', label: 'Performance' },
    { id: 'logs', label: `Audit Logs (${logsCount})` },
    { id: 'policies', label: `Policies (${policiesCount})` },
    { id: 'evaluation', label: 'Evaluation Suite' }
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
