import { useState, useEffect, useCallback } from 'react';
import './index.css';

import Header from './components/Header';
import Navbar from './components/Navbar';
import Overview from './components/Overview';
import DetectionAnalytics from './components/DetectionAnalytics';
import LeakagePrevention from './components/LeakagePrevention';
import TokenRestoration from './components/TokenRestoration';
import PerformanceAnalytics from './components/PerformanceAnalytics';
import AuditLogs from './components/AuditLogs';
import PolicyRegistry from './components/PolicyRegistry';
import TestLab from './components/TestLab';
import EvaluationSuite from './components/EvaluationSuite';

import {
  fetchMetrics,
  fetchLogs,
  fetchPolicies,
  runEvaluationBenchmark,
  resetEvaluationData
} from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('active_tab') || 'sandbox');
  const [metrics, setMetrics] = useState(null);
  const [logs, setLogs] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loadingEval, setLoadingEval] = useState(false);
  const [loadingReset, setLoadingReset] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    localStorage.setItem('active_tab', activeTab);
  }, [activeTab]);

  const loadMetrics = useCallback(async () => {
    try {
      const data = await fetchMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
    }
  }, []);

  const loadLogs = useCallback(async () => {
    try {
      const data = await fetchLogs({ limit: 200 });
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, []);

  const loadPolicies = useCallback(async () => {
    try {
      const data = await fetchPolicies();
      setPolicies(data);
    } catch (err) {
      console.error('Failed to fetch policies:', err);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadMetrics(), loadLogs()]);
  }, [loadMetrics, loadLogs]);

  useEffect(() => {
    loadMetrics();
    loadLogs();
    loadPolicies();
  }, []);

  const handleRunEval = async () => {
    setLoadingEval(true);
    setError(null);
    try {
      const data = await runEvaluationBenchmark();
      setMetrics(data);
      await loadLogs();
    } catch (err) {
      setError('Evaluation failed: ' + err.message);
    } finally {
      setLoadingEval(false);
    }
  };

  const handleResetData = async () => {
    if (!window.confirm('Reset all test results, audit logs, token vault, and database records?')) return;
    setLoadingReset(true);
    setError(null);
    try {
      await resetEvaluationData();
      localStorage.removeItem('test_lab_result');
      setMetrics(null);
      setLogs([]);
      await refreshAll();
    } catch (err) {
      setError('Reset failed: ' + err.message);
    } finally {
      setLoadingReset(false);
    }
  };

  const hasMetrics = !!(metrics && metrics.has_data !== false && metrics.total_requests > 0);

  return (
    <div className="app-wrapper">
      <Header
        onRunEval={handleRunEval}
        onResetData={handleResetData}
        loadingEval={loadingEval}
        loadingReset={loadingReset}
        hasMetrics={hasMetrics}
      />
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        logsCount={logs.length}
        policiesCount={policies.length}
      />

      {error && (
        <div style={{ background: 'var(--danger-bg)', color: 'var(--danger)', padding: '0.75rem 2rem', fontSize: '0.875rem', fontWeight: 500 }}>
          ⚠️ {error}
        </div>
      )}

      <main className="main-content">
        <div style={{ display: activeTab === 'sandbox' ? 'block' : 'none' }}>
          <TestLab onRefreshAll={refreshAll} />
        </div>
        <div style={{ display: activeTab === 'overview' ? 'block' : 'none' }}>
          <Overview metrics={metrics} />
        </div>
        <div style={{ display: activeTab === 'detection' ? 'block' : 'none' }}>
          <DetectionAnalytics metrics={metrics} />
        </div>
        <div style={{ display: activeTab === 'leakage' ? 'block' : 'none' }}>
          <LeakagePrevention metrics={metrics} />
        </div>
        <div style={{ display: activeTab === 'restoration' ? 'block' : 'none' }}>
          <TokenRestoration metrics={metrics} onRefreshMetrics={loadMetrics} />
        </div>
        <div style={{ display: activeTab === 'performance' ? 'block' : 'none' }}>
          <PerformanceAnalytics metrics={metrics} />
        </div>
        <div style={{ display: activeTab === 'logs' ? 'block' : 'none' }}>
          <AuditLogs logs={logs} />
        </div>
        <div style={{ display: activeTab === 'policies' ? 'block' : 'none' }}>
          <PolicyRegistry policies={policies} />
        </div>
        <div style={{ display: activeTab === 'evaluation' ? 'block' : 'none' }}>
          <EvaluationSuite
            metrics={metrics}
            onRunEval={handleRunEval}
            onResetData={handleResetData}
            loadingEval={loadingEval}
            loadingReset={loadingReset}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
