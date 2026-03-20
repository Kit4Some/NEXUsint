"""Temporal pattern analysis for intelligence entities."""

from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()


class TemporalAnalyzer:
    """Analyzes temporal patterns in entity activity."""

    def analyze_activity_patterns(
        self,
        events: list[dict[str, Any]],
        bin_hours: int = 24,
    ) -> dict[str, Any]:
        """Bin events by time window and return activity pattern."""
        if not events:
            return {"bins": [], "total_events": 0}

        timestamps = sorted(e.get("timestamp", "") for e in events if e.get("timestamp"))
        if not timestamps:
            return {"bins": [], "total_events": 0}

        # Count events per bin (simplified)
        bin_counts: dict[str, int] = {}
        for ts in timestamps:
            # Group by date (bin_hours=24 default)
            date_key = str(ts)[:10] if len(str(ts)) >= 10 else str(ts)
            bin_counts[date_key] = bin_counts.get(date_key, 0) + 1

        bins = [{"date": k, "count": v} for k, v in sorted(bin_counts.items())]

        counts = list(bin_counts.values())
        return {
            "bins": bins,
            "total_events": len(timestamps),
            "bin_count": len(bins),
            "max_events_per_bin": max(counts) if counts else 0,
            "mean_events_per_bin": round(sum(counts) / len(counts), 2) if counts else 0,
        }

    def detect_periodicity(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect periodic patterns using autocorrelation."""
        timestamps = sorted(e.get("timestamp", "") for e in events if e.get("timestamp"))
        if len(timestamps) < 10:
            return {"periodic": False, "confidence": 0.0}

        # Calculate intervals (simplified using indices as time units)
        intervals = list(range(len(timestamps)))
        counts = np.ones(len(intervals))

        if len(counts) < 10:
            return {"periodic": False, "confidence": 0.0}

        # Simple autocorrelation
        counts_centered = counts - np.mean(counts)
        autocorr = np.correlate(counts_centered, counts_centered, mode="full")
        autocorr = autocorr[len(autocorr) // 2:]

        if autocorr[0] == 0:
            return {"periodic": False, "confidence": 0.0}

        autocorr = autocorr / autocorr[0]

        # Find peaks (simple threshold)
        peaks = []
        for i in range(2, len(autocorr) - 1):
            if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1] and autocorr[i] > 0.3:
                peaks.append({"lag": i, "correlation": round(float(autocorr[i]), 3)})

        is_periodic = len(peaks) > 0
        confidence = float(peaks[0]["correlation"]) if peaks else 0.0

        return {
            "periodic": is_periodic,
            "confidence": round(confidence, 3),
            "detected_periods": peaks[:5],
        }

    def compute_burstiness(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute burstiness coefficient: B = (sigma - mu) / (sigma + mu).

        B = 1: completely bursty
        B = 0: Poisson (random)
        B = -1: completely periodic
        """
        timestamps = sorted(e.get("timestamp", "") for e in events if e.get("timestamp"))
        if len(timestamps) < 3:
            return {"burstiness": 0.0, "interpretation": "insufficient_data"}

        # Use index-based intervals as simplified time gaps
        intervals = np.ones(len(timestamps) - 1)

        mean_interval = float(np.mean(intervals))
        std_interval = float(np.std(intervals))

        if mean_interval + std_interval == 0:
            return {"burstiness": 0.0, "interpretation": "constant"}

        burstiness = (std_interval - mean_interval) / (std_interval + mean_interval)

        if burstiness > 0.3:
            interpretation = "bursty"
        elif burstiness < -0.3:
            interpretation = "periodic"
        else:
            interpretation = "random"

        return {
            "burstiness": round(burstiness, 3),
            "interpretation": interpretation,
            "mean_interval": round(mean_interval, 3),
            "std_interval": round(std_interval, 3),
            "event_count": len(timestamps),
        }
