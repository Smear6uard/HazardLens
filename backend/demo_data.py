"""
Pre-computed demo data: a narrative arc over 500 frames (~2 min at 10 FPS).

Phase 1 (0-100):   4 workers, all compliant, normal activity
Phase 2 (100-200):  1 worker removes hardhat (PPE violation events)
Phase 3 (200-300):  Vehicle enters restricted zone (zone violation)
Phase 4 (300-400):  Near-miss between worker and vehicle (critical alerts)
Phase 5 (400-500):  Compliance restored, risk score drops

Generates synthetic frames with OpenCV drawing primitives — no model needed.
"""

from __future__ import annotations

import base64
import math
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from models import (
    Analytics,
    Detection,
    Event,
    FrameResult,
    ObjectClass,
    PPEStatus,
    Severity,
    TimeSeriesPoint,
    TrackedObject,
    ZoneConfig,
)

FRAME_W, FRAME_H = 960, 540
TOTAL_FRAMES = 500
FPS = 10

# predefined zones
RESTRICTED_ZONE = ZoneConfig(
    id="zone_r1",
    name="Equipment Storage",
    zone_type="restricted",
    polygon=[(600, 200), (900, 200), (900, 450), (600, 450)],
    color=(0, 0, 200),
)
DANGER_ZONE = ZoneConfig(
    id="zone_d1",
    name="Crane Operation Area",
    zone_type="danger",
    polygon=[(50, 350), (350, 350), (350, 500), (50, 500)],
    color=(0, 0, 255),
)


@dataclass
class _Worker:
    track_id: int
    x: float
    y: float
    w: float = 40.0
    h: float = 90.0
    ppe: PPEStatus = PPEStatus.HARDHAT_ON
    vx: float = 0.0
    vy: float = 0.0

    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def centroid(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)


@dataclass
class _Vehicle:
    track_id: int
    x: float
    y: float
    w: float = 80.0
    h: float = 50.0
    vx: float = 0.0
    vy: float = 0.0

    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def centroid(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)


def _draw_frame(
    workers: list[_Worker],
    vehicle: _Vehicle | None,
    zones: list[ZoneConfig],
    frame_num: int,
    events: list[Event],
    risk_score: float,
    compliance_rate: float,
) -> np.ndarray:
    """Render a synthetic frame."""
    # dark gray construction-site background
    frame = np.full((FRAME_H, FRAME_W, 3), (45, 42, 40), dtype=np.uint8)

    # draw ground grid lines for perspective feel
    for gx in range(0, FRAME_W, 60):
        cv2.line(frame, (gx, 0), (gx, FRAME_H), (55, 52, 50), 1)
    for gy in range(0, FRAME_H, 60):
        cv2.line(frame, (0, gy), (FRAME_W, gy), (55, 52, 50), 1)

    # draw zone overlays
    overlay = frame.copy()
    for zone in zones:
        pts = np.array(zone.polygon, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], zone.color)
        cv2.polylines(frame, [pts], True, zone.color, 2, cv2.LINE_AA)
        cx = int(np.mean([p[0] for p in zone.polygon]))
        cy = int(np.mean([p[1] for p in zone.polygon])) - 10
        cv2.putText(
            frame, zone.name, (cx - 40, cy),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
        )
    frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

    # draw vehicle
    if vehicle is not None:
        vx1, vy1, vx2, vy2 = (int(v) for v in vehicle.bbox())
        cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (255, 150, 50), 2, cv2.LINE_AA)
        cv2.rectangle(frame, (vx1 + 2, vy1 + 2), (vx2 - 2, vy2 - 2), (200, 120, 40), -1)
        # wheels
        cv2.circle(frame, (vx1 + 12, vy2), 6, (80, 80, 80), -1, cv2.LINE_AA)
        cv2.circle(frame, (vx2 - 12, vy2), 6, (80, 80, 80), -1, cv2.LINE_AA)
        label = f"#{vehicle.track_id} truck"
        cv2.putText(
            frame, label, (vx1, vy1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 150, 50), 1, cv2.LINE_AA,
        )

    # draw workers
    for w in workers:
        x1, y1, x2, y2 = (int(v) for v in w.bbox())
        if w.ppe == PPEStatus.HARDHAT_ON:
            border_color = (0, 200, 0)
            body_color = (0, 160, 0)
            hat_color = (0, 220, 220)  # yellow hardhat
        else:
            border_color = (0, 0, 255)
            body_color = (0, 0, 200)
            hat_color = None

        # body
        cv2.rectangle(frame, (x1, y1 + 15), (x2, y2), body_color, -1)
        cv2.rectangle(frame, (x1, y1 + 15), (x2, y2), border_color, 2, cv2.LINE_AA)

        # head
        head_cx, head_cy = int(w.x + w.w / 2), int(w.y + 8)
        cv2.circle(frame, (head_cx, head_cy), 8, (180, 160, 140), -1, cv2.LINE_AA)

        # hardhat
        if hat_color:
            cv2.ellipse(frame, (head_cx, head_cy - 3), (10, 6), 0, 180, 360, hat_color, -1, cv2.LINE_AA)

        # label
        ppe_tag = "OK" if w.ppe == PPEStatus.HARDHAT_ON else "NO HAT"
        label = f"#{w.track_id} [{ppe_tag}]"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), border_color, -1)
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA,
        )

    # HUD overlay
    hud_y = 20
    cv2.putText(
        frame, f"Frame {frame_num}/{TOTAL_FRAMES}", (10, hud_y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA,
    )
    risk_color = (
        (0, 200, 0) if risk_score < 30
        else (0, 180, 255) if risk_score < 60
        else (0, 0, 255)
    )
    cv2.putText(
        frame, f"Risk: {risk_score:.0f}/100", (10, hud_y + 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 1, cv2.LINE_AA,
    )
    comp_color = (0, 200, 0) if compliance_rate > 0.8 else (0, 0, 255)
    cv2.putText(
        frame, f"Compliance: {compliance_rate:.0%}", (10, hud_y + 44),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, comp_color, 1, cv2.LINE_AA,
    )

    # event ticker at bottom
    if events:
        latest = events[-1]
        sev_color = {
            Severity.INFO: (200, 200, 0),
            Severity.WARNING: (0, 165, 255),
            Severity.CRITICAL: (0, 0, 255),
        }.get(latest.severity, (200, 200, 200))
        cv2.rectangle(frame, (0, FRAME_H - 28), (FRAME_W, FRAME_H), (30, 30, 30), -1)
        cv2.putText(
            frame,
            f"[{latest.severity.value.upper()}] {latest.description}",
            (10, FRAME_H - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, sev_color, 1, cv2.LINE_AA,
        )

    return frame


def generate_demo_data() -> tuple[list[FrameResult], list[Event], Analytics]:
    """Generate the full 500-frame demo sequence."""
    zones = [RESTRICTED_ZONE, DANGER_ZONE]

    # workers: 4 people doing various paths
    workers = [
        _Worker(track_id=0, x=100, y=100),
        _Worker(track_id=1, x=200, y=150),
        _Worker(track_id=2, x=400, y=250),
        _Worker(track_id=3, x=500, y=120),
    ]

    vehicle: _Vehicle | None = None
    all_results: list[FrameResult] = []
    all_events: list[Event] = []

    # analytics accumulators
    risk_history: list[TimeSeriesPoint] = []
    compliance_history: list[TimeSeriesPoint] = []
    event_type_counts: dict[str, int] = {}
    total_critical = 0
    total_warning = 0
    total_info = 0

    base_time = time.time()

    for f in range(TOTAL_FRAMES):
        t = f / FPS
        frame_events: list[Event] = []

        # ── Phase logic ──────────────────────────────────────────

        # gentle sinusoidal wander for all workers
        for i, w in enumerate(workers):
            angle = (f * 0.02) + i * 1.5
            w.x += math.sin(angle) * 1.5
            w.y += math.cos(angle + 0.7) * 1.0
            # clamp
            w.x = max(20, min(FRAME_W - w.w - 20, w.x))
            w.y = max(20, min(FRAME_H - w.h - 20, w.y))

        # Phase 2: worker 1 removes hardhat at frame 100
        if f == 100:
            workers[1].ppe = PPEStatus.HARDHAT_OFF
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="ppe_violation",
                    severity=Severity.WARNING,
                    description="Worker #1 removed hardhat",
                    track_id=1,
                    bbox=workers[1].bbox(),
                )
            )
        # periodic PPE violation reminders
        if 100 < f < 200 and f % 30 == 0:
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="ppe_violation",
                    severity=Severity.WARNING,
                    description="Worker #1 still without hardhat",
                    track_id=1,
                    bbox=workers[1].bbox(),
                )
            )

        # Phase 3: vehicle enters at frame 200, moves into restricted zone
        if f == 200:
            vehicle = _Vehicle(track_id=10, x=950, y=300)
        if vehicle and 200 <= f <= 300:
            vehicle.x -= 2.5
            vehicle.x = max(50, vehicle.x)
        if f == 230:
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="zone_entry",
                    severity=Severity.WARNING,
                    description="Vehicle #10 entered restricted zone 'Equipment Storage'",
                    track_id=10,
                    zone_id="zone_r1",
                    bbox=vehicle.bbox() if vehicle else None,
                )
            )

        # Phase 4: near-miss scenario (frames 300-400)
        if vehicle and 300 <= f <= 400:
            # vehicle moves toward worker #2
            target_x, target_y = workers[2].x + 50, workers[2].y
            dx = (target_x - vehicle.x) * 0.02
            dy = (target_y - vehicle.y) * 0.02
            vehicle.x += dx
            vehicle.y += dy

        if f == 320:
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="near_miss",
                    severity=Severity.CRITICAL,
                    description="Near-miss: Worker #2 within 45px of vehicle #10",
                    track_id=2,
                    bbox=workers[2].bbox(),
                )
            )
        if f == 350:
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="near_miss",
                    severity=Severity.CRITICAL,
                    description="Near-miss: Worker #2 within 30px of vehicle #10",
                    track_id=2,
                    bbox=workers[2].bbox(),
                )
            )

        # Phase 5: compliance restoration (frames 400+)
        if f == 400:
            workers[1].ppe = PPEStatus.HARDHAT_ON
            frame_events.append(
                Event(
                    job_id="demo",
                    frame_number=f,
                    event_type="ppe_restored",
                    severity=Severity.INFO,
                    description="Worker #1 put on hardhat",
                    track_id=1,
                    bbox=workers[1].bbox(),
                )
            )
        if vehicle and f >= 420:
            vehicle.x += 3.0
            if vehicle.x > FRAME_W + 100:
                vehicle = None

        # ── Compute risk & compliance ────────────────────────────

        persons_compliant = sum(
            1 for w in workers if w.ppe == PPEStatus.HARDHAT_ON
        )
        compliance_rate = persons_compliant / len(workers) if workers else 1.0

        # risk score based on current phase
        if f < 100:
            risk_score = 6.0 + math.sin(f * 0.05) * 3
        elif f < 200:
            risk_score = 30.0 + math.sin(f * 0.03) * 5
        elif f < 300:
            risk_score = 50.0 + math.sin(f * 0.04) * 8
        elif f < 400:
            risk_score = 75.0 + math.sin(f * 0.05) * 10
        else:
            decay = (f - 400) / 100.0
            risk_score = max(5.0, 75.0 * (1.0 - decay) + math.sin(f * 0.05) * 3)

        risk_score = max(0.0, min(100.0, risk_score))

        # ── Build tracked objects list ───────────────────────────

        tracked: list[TrackedObject] = []
        for w in workers:
            tracked.append(
                TrackedObject(
                    track_id=w.track_id,
                    class_name=ObjectClass.PERSON,
                    bbox=w.bbox(),
                    centroid=w.centroid(),
                    confidence=0.88,
                    ppe_status=w.ppe,
                    velocity=(float(w.vx), float(w.vy)),
                )
            )
        if vehicle:
            tracked.append(
                TrackedObject(
                    track_id=vehicle.track_id,
                    class_name=ObjectClass.TRUCK,
                    bbox=vehicle.bbox(),
                    centroid=vehicle.centroid(),
                    confidence=0.92,
                    velocity=(float(vehicle.vx), float(vehicle.vy)),
                )
            )

        # ── Render frame ─────────────────────────────────────────

        img = _draw_frame(
            workers, vehicle, zones, f, frame_events, risk_score, compliance_rate
        )
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
        b64 = base64.b64encode(buf).decode("utf-8")

        result = FrameResult(
            frame_number=f,
            tracked_objects=tracked,
            events=frame_events,
            risk_score=float(risk_score),
            compliance_rate=float(compliance_rate),
            annotated_frame_b64=b64,
        )
        all_results.append(result)
        all_events.extend(frame_events)

        # analytics tracking
        ts_val = base_time + t
        risk_history.append(TimeSeriesPoint(timestamp=ts_val, value=risk_score))
        compliance_history.append(
            TimeSeriesPoint(timestamp=ts_val, value=compliance_rate)
        )
        for ev in frame_events:
            event_type_counts[ev.event_type] = (
                event_type_counts.get(ev.event_type, 0) + 1
            )
            if ev.severity == Severity.CRITICAL:
                total_critical += 1
            elif ev.severity == Severity.WARNING:
                total_warning += 1
            else:
                total_info += 1

    # build final analytics
    risk_vals = [p.value for p in risk_history]
    comp_vals = [p.value for p in compliance_history]
    analytics = Analytics(
        total_detections=TOTAL_FRAMES * len(workers),
        total_events=len(all_events),
        critical_events=total_critical,
        warning_events=total_warning,
        info_events=total_info,
        avg_risk_score=float(sum(risk_vals) / len(risk_vals)),
        peak_risk_score=float(max(risk_vals)),
        compliance_rate=float(sum(comp_vals) / len(comp_vals)),
        ppe_violations=event_type_counts.get("ppe_violation", 0),
        zone_violations=event_type_counts.get("zone_entry", 0),
        near_misses=event_type_counts.get("near_miss", 0),
        fallen_workers=event_type_counts.get("fallen_worker", 0),
        risk_over_time=risk_history[::5],  # downsample for transport
        compliance_over_time=compliance_history[::5],
        alerts_per_minute=[
            TimeSeriesPoint(timestamp=base_time, value=3.0),
            TimeSeriesPoint(timestamp=base_time + 60, value=5.0),
        ],
        event_type_counts=event_type_counts,
    )

    return all_results, all_events, analytics
