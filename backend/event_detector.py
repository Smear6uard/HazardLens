from __future__ import annotations

import time
from typing import Optional

from config import settings
from models import Event, ObjectClass, PPEStatus, Severity, TrackedObject, ZoneConfig


class EventDetector:
    def __init__(self) -> None:
        # track_id → last known PPE status
        self._prev_ppe: dict[int, PPEStatus] = {}
        # track_id → (first_stationary_time, last_alert_time)
        self._loiter_state: dict[int, tuple[float, float]] = {}
        # (person_id, vehicle_id) → last alert time
        self._near_miss_cooldown: dict[tuple[int, int], float] = {}
        # track_id → consecutive fallen frame count
        self._fallen_counts: dict[int, int] = {}
        # track_id → whether we already fired a fallen alert
        self._fallen_alerted: dict[int, bool] = {}

    def detect_events(
        self,
        tracked_objects: list[TrackedObject],
        zone_entries: dict[int, set[str]],
        zone_exits: dict[int, set[str]],
        proximity_pairs: list[tuple[int, int, float]],
        zones: dict[str, ZoneConfig],
        frame_number: int,
        job_id: str = "",
    ) -> list[Event]:
        events: list[Event] = []
        now = time.time()

        obj_map = {o.track_id: o for o in tracked_objects}

        # PPE transitions
        for obj in tracked_objects:
            if obj.class_name != ObjectClass.PERSON:
                continue
            prev = self._prev_ppe.get(obj.track_id, PPEStatus.UNKNOWN)
            if prev == PPEStatus.HARDHAT_ON and obj.ppe_status == PPEStatus.HARDHAT_OFF:
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="ppe_violation",
                        severity=Severity.WARNING,
                        description=f"Worker #{obj.track_id} removed hardhat",
                        track_id=obj.track_id,
                        bbox=obj.bbox,
                    )
                )
            elif prev == PPEStatus.HARDHAT_OFF and obj.ppe_status == PPEStatus.HARDHAT_ON:
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="ppe_restored",
                        severity=Severity.INFO,
                        description=f"Worker #{obj.track_id} put on hardhat",
                        track_id=obj.track_id,
                        bbox=obj.bbox,
                    )
                )
            self._prev_ppe[obj.track_id] = obj.ppe_status

        # Zone entry/exit events
        for tid, zone_ids in zone_entries.items():
            obj = obj_map.get(tid)
            for zid in zone_ids:
                zone = zones.get(zid)
                zone_name = zone.name if zone else zid
                zone_type = zone.zone_type if zone else "restricted"
                sev = Severity.CRITICAL if zone_type == "danger" else Severity.WARNING
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="zone_entry",
                        severity=sev,
                        description=f"Object #{tid} entered {zone_type} zone '{zone_name}'",
                        track_id=tid,
                        zone_id=zid,
                        bbox=obj.bbox if obj else None,
                    )
                )

        for tid, zone_ids in zone_exits.items():
            obj = obj_map.get(tid)
            for zid in zone_ids:
                zone = zones.get(zid)
                zone_name = zone.name if zone else zid
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="zone_exit",
                        severity=Severity.INFO,
                        description=f"Object #{tid} exited zone '{zone_name}'",
                        track_id=tid,
                        zone_id=zid,
                        bbox=obj.bbox if obj else None,
                    )
                )

        # Loitering detection
        for obj in tracked_objects:
            if obj.class_name != ObjectClass.PERSON:
                continue
            if not obj.in_zones:
                self._loiter_state.pop(obj.track_id, None)
                continue
            # check if person is roughly stationary (low velocity)
            speed = (obj.velocity[0] ** 2 + obj.velocity[1] ** 2) ** 0.5
            if speed < 3.0:
                state = self._loiter_state.get(obj.track_id)
                if state is None:
                    self._loiter_state[obj.track_id] = (now, 0.0)
                else:
                    first_time, last_alert = state
                    elapsed = now - first_time
                    if (
                        elapsed >= settings.LOITER_SECONDS
                        and now - last_alert >= settings.LOITER_COOLDOWN
                    ):
                        events.append(
                            Event(
                                job_id=job_id,
                                frame_number=frame_number,
                                event_type="loitering",
                                severity=Severity.WARNING,
                                description=f"Worker #{obj.track_id} loitering in zone for {elapsed:.0f}s",
                                track_id=obj.track_id,
                                bbox=obj.bbox,
                            )
                        )
                        self._loiter_state[obj.track_id] = (first_time, now)
            else:
                self._loiter_state.pop(obj.track_id, None)

        # Near-miss detection
        for person_id, vehicle_id, dist in proximity_pairs:
            key = (person_id, vehicle_id)
            last = self._near_miss_cooldown.get(key, 0.0)
            if now - last >= settings.NEAR_MISS_COOLDOWN:
                person = obj_map.get(person_id)
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="near_miss",
                        severity=Severity.CRITICAL,
                        description=f"Near-miss: Worker #{person_id} within {dist:.0f}px of vehicle #{vehicle_id}",
                        track_id=person_id,
                        bbox=person.bbox if person else None,
                    )
                )
                self._near_miss_cooldown[key] = now

        # Fallen worker detection
        for obj in tracked_objects:
            if obj.class_name != ObjectClass.PERSON:
                continue
            if obj.is_fallen:
                self._fallen_counts[obj.track_id] = (
                    self._fallen_counts.get(obj.track_id, 0) + 1
                )
            else:
                self._fallen_counts[obj.track_id] = 0
                self._fallen_alerted[obj.track_id] = False

            if (
                self._fallen_counts.get(obj.track_id, 0) >= settings.FALLEN_FRAME_COUNT
                and not self._fallen_alerted.get(obj.track_id, False)
            ):
                events.append(
                    Event(
                        job_id=job_id,
                        frame_number=frame_number,
                        event_type="fallen_worker",
                        severity=Severity.CRITICAL,
                        description=f"Worker #{obj.track_id} may have fallen",
                        track_id=obj.track_id,
                        bbox=obj.bbox,
                    )
                )
                self._fallen_alerted[obj.track_id] = True

        return events

    def reset(self) -> None:
        self._prev_ppe.clear()
        self._loiter_state.clear()
        self._near_miss_cooldown.clear()
        self._fallen_counts.clear()
        self._fallen_alerted.clear()
