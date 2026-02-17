from __future__ import annotations

import time

from models import Analytics, Event, ObjectClass, PPEStatus, Severity, TimeSeriesPoint, TrackedObject


class AnalyticsEngine:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._risk_history: list[TimeSeriesPoint] = []
        self._compliance_history: list[TimeSeriesPoint] = []
        self._alert_buckets: dict[int, int] = {}  # minute bucket → count
        self._start_time: float = time.time()

    def ingest_frame(
        self,
        tracked_objects: list[TrackedObject],
        events: list[Event],
        frame_number: int,
    ) -> tuple[float, float]:
        """Process a frame's data and return (risk_score, compliance_rate)."""
        self._events.extend(events)

        # track alert-per-minute buckets
        elapsed = time.time() - self._start_time
        minute_bucket = int(elapsed / 60)
        for _ in events:
            self._alert_buckets[minute_bucket] = (
                self._alert_buckets.get(minute_bucket, 0) + 1
            )

        # compliance: ratio of hardhat-on persons to all persons
        persons = [
            o for o in tracked_objects if o.class_name == ObjectClass.PERSON
        ]
        if persons:
            compliant = sum(
                1 for p in persons if p.ppe_status == PPEStatus.HARDHAT_ON
            )
            compliance_rate = compliant / len(persons)
        else:
            compliance_rate = 1.0

        # risk score 0-100
        risk_score = self._compute_risk(tracked_objects, events, compliance_rate)

        ts = time.time()
        self._risk_history.append(TimeSeriesPoint(timestamp=ts, value=risk_score))
        self._compliance_history.append(
            TimeSeriesPoint(timestamp=ts, value=compliance_rate)
        )

        return float(risk_score), float(compliance_rate)

    def _compute_risk(
        self,
        tracked_objects: list[TrackedObject],
        recent_events: list[Event],
        compliance_rate: float,
    ) -> float:
        # 40% PPE non-compliance
        ppe_component = (1.0 - compliance_rate) * 40.0

        # 25% zone violations (from recent events)
        zone_violations = sum(
            1 for e in recent_events if e.event_type == "zone_entry"
        )
        zone_component = min(zone_violations * 8.0, 25.0)

        # 25% near-misses
        near_misses = sum(
            1 for e in recent_events if e.event_type == "near_miss"
        )
        near_miss_component = min(near_misses * 12.5, 25.0)

        # 10% worker density (more workers in frame → higher density risk)
        persons = [
            o for o in tracked_objects if o.class_name == ObjectClass.PERSON
        ]
        density_component = min(len(persons) * 1.5, 10.0)

        return min(
            ppe_component + zone_component + near_miss_component + density_component,
            100.0,
        )

    def get_analytics(self) -> Analytics:
        all_events = self._events
        critical = sum(1 for e in all_events if e.severity == Severity.CRITICAL)
        warning = sum(1 for e in all_events if e.severity == Severity.WARNING)
        info = sum(1 for e in all_events if e.severity == Severity.INFO)

        ppe_violations = sum(
            1 for e in all_events if e.event_type == "ppe_violation"
        )
        zone_violations = sum(
            1 for e in all_events if e.event_type == "zone_entry"
        )
        near_misses = sum(
            1 for e in all_events if e.event_type == "near_miss"
        )
        fallen = sum(
            1 for e in all_events if e.event_type == "fallen_worker"
        )

        risk_vals = [p.value for p in self._risk_history]
        avg_risk = sum(risk_vals) / len(risk_vals) if risk_vals else 0.0
        peak_risk = max(risk_vals) if risk_vals else 0.0

        comp_vals = [p.value for p in self._compliance_history]
        avg_compliance = (
            sum(comp_vals) / len(comp_vals) if comp_vals else 1.0
        )

        # event type counts
        type_counts: dict[str, int] = {}
        for e in all_events:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

        # alerts per minute time series
        apm: list[TimeSeriesPoint] = []
        for bucket, count in sorted(self._alert_buckets.items()):
            apm.append(
                TimeSeriesPoint(
                    timestamp=self._start_time + bucket * 60, value=float(count)
                )
            )

        return Analytics(
            total_detections=len(self._events),
            total_events=len(all_events),
            critical_events=critical,
            warning_events=warning,
            info_events=info,
            avg_risk_score=float(avg_risk),
            peak_risk_score=float(peak_risk),
            compliance_rate=float(avg_compliance),
            ppe_violations=ppe_violations,
            zone_violations=zone_violations,
            near_misses=near_misses,
            fallen_workers=fallen,
            risk_over_time=self._risk_history[-200:],
            compliance_over_time=self._compliance_history[-200:],
            alerts_per_minute=apm,
            event_type_counts=type_counts,
        )

    def reset(self) -> None:
        self._events.clear()
        self._risk_history.clear()
        self._compliance_history.clear()
        self._alert_buckets.clear()
        self._start_time = time.time()
