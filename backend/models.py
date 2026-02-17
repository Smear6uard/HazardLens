from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PPEStatus(str, Enum):
    HARDHAT_ON = "hardhat_on"
    HARDHAT_OFF = "hardhat_off"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ObjectClass(str, Enum):
    PERSON = "person"
    BICYCLE = "bicycle"
    CAR = "car"
    TRUCK = "truck"


class Detection(BaseModel):
    class_name: ObjectClass
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    ppe_status: PPEStatus = PPEStatus.UNKNOWN


class TrackedObject(BaseModel):
    track_id: int
    class_name: ObjectClass
    bbox: tuple[float, float, float, float]
    centroid: tuple[float, float]
    confidence: float
    ppe_status: PPEStatus = PPEStatus.UNKNOWN
    velocity: tuple[float, float] = (0.0, 0.0)
    trajectory: list[tuple[float, float]] = Field(default_factory=list)
    is_fallen: bool = False
    in_zones: list[str] = Field(default_factory=list)


class ZoneConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    zone_type: str = "restricted"  # restricted | danger | safe
    polygon: list[tuple[float, float]]
    color: tuple[int, int, int] = (0, 0, 255)


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    job_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    frame_number: int = 0
    event_type: str
    severity: Severity
    description: str
    track_id: Optional[int] = None
    zone_id: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None


class FrameResult(BaseModel):
    frame_number: int
    detections: list[Detection] = Field(default_factory=list)
    tracked_objects: list[TrackedObject] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    risk_score: float = 0.0
    compliance_rate: float = 1.0
    annotated_frame_b64: str = ""


class TimeSeriesPoint(BaseModel):
    timestamp: float
    value: float


class Analytics(BaseModel):
    total_detections: int = 0
    total_events: int = 0
    critical_events: int = 0
    warning_events: int = 0
    info_events: int = 0
    avg_risk_score: float = 0.0
    peak_risk_score: float = 0.0
    compliance_rate: float = 1.0
    ppe_violations: int = 0
    zone_violations: int = 0
    near_misses: int = 0
    fallen_workers: int = 0
    risk_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    compliance_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    alerts_per_minute: list[TimeSeriesPoint] = Field(default_factory=list)
    event_type_counts: dict[str, int] = Field(default_factory=dict)


class JobStatus(BaseModel):
    job_id: str
    status: str = "queued"  # queued | processing | complete | error
    progress: float = 0.0
    total_frames: int = 0
    processed_frames: int = 0
    error: Optional[str] = None


class SettingsUpdate(BaseModel):
    confidence_threshold: Optional[float] = None
    skip_frames: Optional[int] = None
    proximity_threshold: Optional[float] = None
    loiter_seconds: Optional[float] = None
    stream_fps: Optional[int] = None
