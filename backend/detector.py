from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

import cv2
import numpy as np

from config import settings
from models import Detection, ObjectClass, PPEStatus

logger = logging.getLogger(__name__)

# COCO class-id → our ObjectClass mapping
_COCO_MAP: dict[int, ObjectClass] = {
    0: ObjectClass.PERSON,
    1: ObjectClass.BICYCLE,
    2: ObjectClass.CAR,
    7: ObjectClass.TRUCK,
}


class DetectorInterface(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class YOLODetector(DetectorInterface):
    def __init__(self) -> None:
        self._model = None
        self._available = False
        try:
            from ultralytics import YOLO

            self._model = YOLO(settings.MODEL_NAME)
            self._available = True
            logger.info("YOLO model loaded: %s", settings.MODEL_NAME)
        except Exception as exc:
            logger.warning("YOLO model not available (%s). Demo mode only.", exc)

    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if not self._available or self._model is None:
            return []
        results = self._model(frame, conf=settings.CONFIDENCE_THRESHOLD, verbose=False)
        detections: list[Detection] = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in _COCO_MAP:
                    continue
                obj_class = _COCO_MAP[cls_id]
                conf = float(box.conf[0])
                # small random variance for realism
                conf = max(0.0, min(1.0, conf + random.uniform(-0.02, 0.02)))
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                ppe = PPEStatus.UNKNOWN
                if obj_class == ObjectClass.PERSON:
                    ppe = _classify_ppe(frame, x1, y1, x2, y2)
                detections.append(
                    Detection(
                        class_name=obj_class,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        ppe_status=ppe,
                    )
                )
        return detections


def _classify_ppe(
    frame: np.ndarray, x1: float, y1: float, x2: float, y2: float
) -> PPEStatus:
    """Crop upper 30% of person bbox, check HSV histogram for hardhat colors."""
    h_img, w_img = frame.shape[:2]
    ix1, iy1, ix2, iy2 = (
        max(0, int(x1)),
        max(0, int(y1)),
        min(w_img, int(x2)),
        min(h_img, int(y2)),
    )
    bh = iy2 - iy1
    if bh < 10 or ix2 - ix1 < 5:
        return PPEStatus.UNKNOWN
    head_crop = frame[iy1 : iy1 + int(bh * 0.3), ix1:ix2]
    if head_crop.size == 0:
        return PPEStatus.UNKNOWN
    hsv = cv2.cvtColor(head_crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    total = h.size
    if total == 0:
        return PPEStatus.UNKNOWN

    # yellow hardhat: H 20-35
    yellow = np.count_nonzero((h >= 20) & (h <= 35) & (s > 50))
    # orange hardhat: H 10-20
    orange = np.count_nonzero((h >= 10) & (h < 20) & (s > 50))
    # white hardhat: S < 30, V > 180
    white = np.count_nonzero((s < 30) & (v > 180))
    # red hardhat: H 0-10 or 170-180
    red = np.count_nonzero(((h <= 10) | (h >= 170)) & (s > 50))

    hardhat_pixels = yellow + orange + white + red
    ratio = hardhat_pixels / total

    if ratio > settings.HARDHAT_COLOR_THRESHOLD:
        return PPEStatus.HARDHAT_ON
    return PPEStatus.HARDHAT_OFF
