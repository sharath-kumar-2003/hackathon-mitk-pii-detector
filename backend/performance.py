import time
import statistics
from typing import Dict, Any, List

class PerformanceTracker:
    def __init__(self):
        self.measurements: List[Dict[str, Any]] = []

    def clear(self):
        self.measurements.clear()

    def record_run(self, baseline_ms: float, protected_ms: float, stage_breakdown: Dict[str, float]) -> Dict[str, Any]:
        added_ms = max(0.0, protected_ms - baseline_ms)
        if baseline_ms > 0.0001:
            overhead_pct = round(((protected_ms - baseline_ms) / baseline_ms) * 100.0, 2)
        else:
            overhead_pct = None # Overhead unavailable if baseline is ~0

        record = {
            "baseline_ms": round(baseline_ms, 3),
            "protected_ms": round(protected_ms, 3),
            "added_ms": round(added_ms, 3),
            "overhead_pct": overhead_pct,
            "stage_breakdown": {k: round(v, 3) for k, v in stage_breakdown.items()}
        }
        self.measurements.append(record)
        return record

    def get_summary_stats(self) -> Dict[str, Any]:
        if not self.measurements:
            return {
                "total_runs": 0,
                "avg_baseline_ms": 0.0,
                "avg_protected_ms": 0.0,
                "median_protected_ms": 0.0,
                "p95_protected_ms": 0.0,
                "avg_added_ms": 0.0,
                "avg_overhead_pct": None,
                "stage_averages": {
                    "detection_ms": 0.0,
                    "policy_ms": 0.0,
                    "transformation_ms": 0.0,
                    "verification_ms": 0.0
                }
            }

        protected_times = [m["protected_ms"] for m in self.measurements]
        baseline_times = [m["baseline_ms"] for m in self.measurements]
        added_times = [m["added_ms"] for m in self.measurements]
        overhead_pcts = [m["overhead_pct"] for m in self.measurements if m["overhead_pct"] is not None]

        sorted_protected = sorted(protected_times)
        n = len(sorted_protected)
        
        # Median
        median_p = statistics.median(sorted_protected) if n > 0 else 0.0

        # p95 (95th percentile)
        p95_idx = int(0.95 * n)
        p95_idx = min(p95_idx, n - 1)
        p95_p = sorted_protected[p95_idx] if n > 0 else 0.0

        avg_baseline = statistics.mean(baseline_times) if baseline_times else 0.0
        avg_protected = statistics.mean(protected_times) if protected_times else 0.0
        avg_added = statistics.mean(added_times) if added_times else 0.0
        avg_overhead = round(statistics.mean(overhead_pcts), 2) if overhead_pcts else None

        # Stage averages
        detection_times = [m["stage_breakdown"].get("detection_ms", 0.0) for m in self.measurements]
        policy_times = [m["stage_breakdown"].get("policy_ms", 0.0) for m in self.measurements]
        trans_times = [m["stage_breakdown"].get("transformation_ms", 0.0) for m in self.measurements]
        verif_times = [m["stage_breakdown"].get("verification_ms", 0.0) for m in self.measurements]

        return {
            "total_runs": n,
            "avg_baseline_ms": round(avg_baseline, 3),
            "avg_protected_ms": round(avg_protected, 3),
            "median_protected_ms": round(median_p, 3),
            "p95_protected_ms": round(p95_p, 3),
            "avg_added_ms": round(avg_added, 3),
            "avg_overhead_pct": avg_overhead,
            "stage_averages": {
                "detection_ms": round(statistics.mean(detection_times), 3) if detection_times else 0.0,
                "policy_ms": round(statistics.mean(policy_times), 3) if policy_times else 0.0,
                "transformation_ms": round(statistics.mean(trans_times), 3) if trans_times else 0.0,
                "verification_ms": round(statistics.mean(verif_times), 3) if verif_times else 0.0
            }
        }
