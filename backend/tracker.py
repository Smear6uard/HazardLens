from __future__ import annotations

from collections import OrderedDict

import numpy as np
from scipy.spatial.distance import cdist

from config import settings
from models import Detection, ObjectClass, TrackedObject


class CentroidTracker:
    def __init__(self) -> None:
        self._next_id: int = 0
        self._objects: OrderedDict[int, TrackedObject] = OrderedDict()
        self._disappeared: dict[int, int] = {}
        self._max_disappeared: int = 15

    @property
    def objects(self) -> dict[int, TrackedObject]:
        return dict(self._objects)

    def update(self, detections: list[Detection]) -> list[TrackedObject]:
        if not detections:
            to_remove = []
            for tid in list(self._disappeared):
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self._max_disappeared:
                    to_remove.append(tid)
            for tid in to_remove:
                self._objects.pop(tid, None)
                self._disappeared.pop(tid, None)
            return list(self._objects.values())

        # compute centroids for incoming detections
        input_centroids = np.array(
            [
                (
                    (d.bbox[0] + d.bbox[2]) / 2.0,
                    (d.bbox[1] + d.bbox[3]) / 2.0,
                )
                for d in detections
            ]
        )

        if len(self._objects) == 0:
            for i, det in enumerate(detections):
                cx, cy = float(input_centroids[i][0]), float(input_centroids[i][1])
                self._register(det, (cx, cy))
        else:
            obj_ids = list(self._objects.keys())
            obj_centroids = np.array(
                [
                    (self._objects[oid].centroid[0], self._objects[oid].centroid[1])
                    for oid in obj_ids
                ]
            )

            D = cdist(obj_centroids, input_centroids)

            # greedy matching: pick the smallest distance first
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows: set[int] = set()
            used_cols: set[int] = set()

            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > settings.MAX_TRACK_DISTANCE:
                    continue
                tid = obj_ids[row]
                det = detections[col]
                cx, cy = float(input_centroids[col][0]), float(input_centroids[col][1])
                self._update_object(tid, det, (cx, cy))
                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(len(obj_ids))) - used_rows
            unused_cols = set(range(len(detections))) - used_cols

            for row in unused_rows:
                tid = obj_ids[row]
                self._disappeared[tid] = self._disappeared.get(tid, 0) + 1
                if self._disappeared[tid] > self._max_disappeared:
                    self._objects.pop(tid, None)
                    self._disappeared.pop(tid, None)

            for col in unused_cols:
                det = detections[col]
                cx, cy = float(input_centroids[col][0]), float(input_centroids[col][1])
                self._register(det, (cx, cy))

        return list(self._objects.values())

    def _register(self, det: Detection, centroid: tuple[float, float]) -> None:
        tid = self._next_id
        self._next_id += 1
        x1, y1, x2, y2 = det.bbox
        w, h = x2 - x1, y2 - y1
        is_fallen = (
            det.class_name == ObjectClass.PERSON and w > h * 1.3
        )
        self._objects[tid] = TrackedObject(
            track_id=tid,
            class_name=det.class_name,
            bbox=det.bbox,
            centroid=centroid,
            confidence=det.confidence,
            ppe_status=det.ppe_status,
            velocity=(0.0, 0.0),
            trajectory=[centroid],
            is_fallen=is_fallen,
        )
        self._disappeared[tid] = 0

    def _update_object(
        self, tid: int, det: Detection, centroid: tuple[float, float]
    ) -> None:
        obj = self._objects[tid]
        old_cx, old_cy = obj.centroid
        vx = centroid[0] - old_cx
        vy = centroid[1] - old_cy

        traj = list(obj.trajectory)
        traj.append(centroid)
        if len(traj) > settings.TRAJECTORY_LENGTH:
            traj = traj[-settings.TRAJECTORY_LENGTH :]

        x1, y1, x2, y2 = det.bbox
        w, h = x2 - x1, y2 - y1
        is_fallen = det.class_name == ObjectClass.PERSON and w > h * 1.3

        self._objects[tid] = TrackedObject(
            track_id=tid,
            class_name=det.class_name,
            bbox=det.bbox,
            centroid=centroid,
            confidence=det.confidence,
            ppe_status=det.ppe_status,
            velocity=(float(vx), float(vy)),
            trajectory=traj,
            is_fallen=is_fallen,
            in_zones=obj.in_zones,
        )
        self._disappeared[tid] = 0

    def reset(self) -> None:
        self._objects.clear()
        self._disappeared.clear()
        self._next_id = 0
