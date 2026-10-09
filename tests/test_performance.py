import pytest
import time
from backend.performance import PerformanceTracker

def test_performance_tracker_calculations():
    tracker = PerformanceTracker()
    
    # Run 1: baseline=2.0ms, protected=10.0ms -> added=8.0ms, overhead=400.0%
    tracker.record_run(2.0, 10.0, {"detection_ms": 3.0, "policy_ms": 1.0, "transformation_ms": 3.0, "verification_ms": 1.0})
    
    # Run 2: baseline=2.0ms, protected=12.0ms -> added=10.0ms, overhead=500.0%
    tracker.record_run(2.0, 12.0, {"detection_ms": 4.0, "policy_ms": 1.0, "transformation_ms": 4.0, "verification_ms": 1.0})

    stats = tracker.get_summary_stats()
    
    assert stats["total_runs"] == 2
    assert stats["avg_baseline_ms"] == 2.0
    assert stats["avg_protected_ms"] == 11.0
    assert stats["median_protected_ms"] == 11.0
    assert stats["p95_protected_ms"] == 12.0
    assert stats["avg_added_ms"] == 9.0
    assert stats["avg_overhead_pct"] == 450.0

def test_performance_zero_baseline_safety():
    tracker = PerformanceTracker()
    # If baseline is 0.0ms (instant), overhead_pct should be None (unavailable), not cause DivisionByZero!
    tracker.record_run(0.0, 5.0, {"detection_ms": 2.0, "policy_ms": 1.0, "transformation_ms": 1.0, "verification_ms": 1.0})
    
    stats = tracker.get_summary_stats()
    assert stats["avg_overhead_pct"] is None
    assert stats["avg_added_ms"] == 5.0
