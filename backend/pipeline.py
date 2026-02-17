from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import AsyncIterator, Callable, Optional

import cv2
import numpy as np

from analytics import AnalyticsEngine
from config import settings
from detector import YOLODetector
from event_detector import EventDetector
from models import (
    Analytics,
    Event,
    FrameResult,
    ObjectClass,
    PPEStatus,
    TrackedObject,
    ZoneConfig,
)
from tracker import CentroidTracker
from zone_engine import ZoneEngine

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self) -> None:
        self.detector = YOLODetector()
        self.tracker = CentroidTracker()
        self.zone_engine = ZoneEngine()
        self.event_detector = EventDetector()
        self.analytics_engine = AnalyticsEngine()
        self._frame_count: int = 0
        self._last_result: Optional[FrameResult] = None

    def process_frame(self, frame: np.ndarray, job_id: str = "") -> FrameResult:
        self._frame_count += 1
        t_start = time.perf_counter()

        # Update zone engine with frame dimensions
        h, w = frame.shape[:2]
        self.zone_engine.set_frame_size(w, h)

        # frame skip: only run YOLO every Nth frame
        if (
            self._frame_count % settings.SKIP_FRAMES != 1
            and self._last_result is not None
        ):
            return self._last_result

        # 1. detect
        t0 = time.perf_counter()
        detections = self.detector.detect(frame)
        t_detect = time.perf_counter() - t0

        # 2. track
        t0 = time.perf_counter()
        tracked = self.tracker.update(detections)
        t_track = time.perf_counter() - t0

        # 3. zone checks
        occupancy, entries, exits = self.zone_engine.check_zones(tracked)

        # 4. proximity
        proximity_pairs = self.zone_engine.detect_proximity(tracked)

        # 5. events
        events = self.event_detector.detect_events(
            tracked_objects=tracked,
            zone_entries=entries,
            zone_exits=exits,
            proximity_pairs=proximity_pairs,
            zones=self.zone_engine.zones,
            frame_number=self._frame_count,
            job_id=job_id,
        )

        # 6. analytics
        risk_score, compliance_rate = self.analytics_engine.ingest_frame(
            tracked, events, self._frame_count
        )

        # 7. annotate
        t0 = time.perf_counter()
        annotated = self._annotate_frame(frame, tracked, events)
        t_annotate = time.perf_counter() - t0

        # 8. encode to base64
        t0 = time.perf_counter()
        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64 = base64.b64encode(buf).decode("utf-8")
        t_encode = time.perf_counter() - t0

        t_total = time.perf_counter() - t_start

        # Timing log every 10 frames
        if self._frame_count % 10 == 1:
            logger.info(
                "Frame %d | det=%.0fms trk=%.1fms ann=%.1fms enc=%.1fms total=%.0fms | "
                "%d detections, %d tracked, %d events, risk=%.1f",
                self._frame_count,
                t_detect * 1000,
                t_track * 1000,
                t_annotate * 1000,
                t_encode * 1000,
                t_total * 1000,
                len(detections),
                len(tracked),
                len(events),
                risk_score,
            )

        result = FrameResult(
            frame_number=self._frame_count,
            detections=detections,
            tracked_objects=tracked,
            events=events,
            risk_score=risk_score,
            compliance_rate=compliance_rate,
            annotated_frame_b64=b64,
        )
        self._last_result = result
        return result

    def _annotate_frame(
        self,
        frame: np.ndarray,
        tracked: list[TrackedObject],
        events: list[Event],
    ) -> np.ndarray:
        overlay = frame.copy()

        # draw zone overlays
        h, w = frame.shape[:2]
        for zid, zone in self.zone_engine.zones.items():
            pts = np.array(
                [[int(x * w), int(y * h)] for x, y in zone.polygon], dtype=np.int32
            )
            color = zone.color
            cv2.fillPoly(overlay, [pts], color)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)

        # draw tracked objects
        for obj in tracked:
            x1, y1, x2, y2 = (int(v) for v in obj.bbox)

            # color-coded bboxes
            if obj.class_name in (ObjectClass.CAR, ObjectClass.TRUCK, ObjectClass.BICYCLE):
                color = (255, 150, 50)  # blue-ish for vehicles
            elif obj.is_fallen:
                color = (0, 0, 255)  # red for fallen
            elif obj.ppe_status == PPEStatus.HARDHAT_ON:
                color = (0, 200, 0)  # green for compliant
            elif obj.ppe_status == PPEStatus.HARDHAT_OFF:
                color = (0, 0, 255)  # red for non-compliant
            else:
                color = (0, 165, 255)  # orange for unknown/partial

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

            # label background
            label = f"#{obj.track_id} {obj.class_name.value}"
            if obj.class_name == ObjectClass.PERSON:
                label += f" [{obj.ppe_status.value}]"
            if obj.is_fallen:
                label += " FALLEN"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1
            )
            cv2.putText(
                frame,
                label,
                (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

            # trajectory trail
            if len(obj.trajectory) > 1:
                pts = [(int(p[0]), int(p[1])) for p in obj.trajectory]
                for i in range(1, len(pts)):
                    thickness = max(1, int(2 * i / len(pts)))
                    cv2.line(frame, pts[i - 1], pts[i], color, thickness, cv2.LINE_AA)

        # draw event labels on frame
        y_offset = 30
        for ev in events:
            sev_color = (0, 0, 255) if ev.severity.value == "critical" else (0, 165, 255) if ev.severity.value == "warning" else (0, 255, 255)
            cv2.putText(
                frame,
                f"[{ev.severity.value.upper()}] {ev.description}",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                sev_color,
                1,
                cv2.LINE_AA,
            )
            y_offset += 22

        return frame

    async def process_video(
        self,
        video_path: str,
        job_id: str = "",
        on_frame: Optional[Callable[[FrameResult], None]] = None,
        on_event: Optional[Callable[[Event], None]] = None,
    ) -> Analytics:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        logger.info(
            "Processing video: %s (%d frames, %.1f fps source)",
            video_path, total_frames, source_fps,
        )
        self.reset()

        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1

                result = self.process_frame(frame, job_id=job_id)

                if on_frame:
                    on_frame(result)
                if on_event:
                    for ev in result.events:
                        on_event(ev)

                # yield control to event loop periodically
                if frame_idx % 5 == 0:
                    await asyncio.sleep(0)
        finally:
            cap.release()

        logger.info("Video processing complete: %d frames processed", frame_idx)
        return self.analytics_engine.get_analytics()

    def get_analytics(self) -> Analytics:
        return self.analytics_engine.get_analytics()

    def reset(self) -> None:
        self.tracker.reset()
        self.event_detector.reset()
        self.analytics_engine.reset()
        self.zone_engine.reset()
        self._frame_count = 0
        self._last_result = None
