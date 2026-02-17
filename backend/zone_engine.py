from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist
from shapely.geometry import Point, Polygon

from config import settings
from models import ObjectClass, TrackedObject, ZoneConfig


class ZoneEngine:
    def __init__(self) -> None:
        self._zones: dict[str, ZoneConfig] = {}
        self._polygons: dict[str, Polygon] = {}
        # track_id → set of zone_ids that object was in on the previous frame
        self._prev_occupancy: dict[int, set[str]] = {}

    @property
    def zones(self) -> dict[str, ZoneConfig]:
        return dict(self._zones)

    def add_zone(self, zone: ZoneConfig) -> None:
        self._zones[zone.id] = zone
        self._polygons[zone.id] = Polygon(zone.polygon)

    def remove_zone(self, zone_id: str) -> bool:
        if zone_id in self._zones:
            del self._zones[zone_id]
            del self._polygons[zone_id]
            return True
        return False

    def check_zones(
        self, tracked_objects: list[TrackedObject]
    ) -> tuple[dict[int, set[str]], dict[int, set[str]], dict[int, set[str]]]:
        """
        Returns (current_occupancy, entries, exits) as dicts of
        track_id → set of zone_ids.
        """
        current: dict[int, set[str]] = {}
        entries: dict[int, set[str]] = {}
        exits: dict[int, set[str]] = {}

        for obj in tracked_objects:
            pt = Point(obj.centroid[0], obj.centroid[1])
            in_zones: set[str] = set()
            for zid, poly in self._polygons.items():
                if poly.contains(pt):
                    in_zones.add(zid)
            current[obj.track_id] = in_zones

            prev = self._prev_occupancy.get(obj.track_id, set())
            entered = in_zones - prev
            exited = prev - in_zones
            if entered:
                entries[obj.track_id] = entered
            if exited:
                exits[obj.track_id] = exited

            # update the tracked object's in_zones list
            obj.in_zones = list(in_zones)

        self._prev_occupancy = current
        return current, entries, exits

    def detect_proximity(
        self, tracked_objects: list[TrackedObject]
    ) -> list[tuple[int, int, float]]:
        """
        Returns list of (person_track_id, vehicle_track_id, distance) pairs
        where distance < PROXIMITY_THRESHOLD.
        """
        persons = [
            o for o in tracked_objects if o.class_name == ObjectClass.PERSON
        ]
        vehicles = [
            o
            for o in tracked_objects
            if o.class_name in (ObjectClass.CAR, ObjectClass.TRUCK, ObjectClass.BICYCLE)
        ]
        if not persons or not vehicles:
            return []

        p_centroids = np.array([[p.centroid[0], p.centroid[1]] for p in persons])
        v_centroids = np.array([[v.centroid[0], v.centroid[1]] for v in vehicles])
        D = cdist(p_centroids, v_centroids)

        close_pairs: list[tuple[int, int, float]] = []
        for pi in range(len(persons)):
            for vi in range(len(vehicles)):
                dist = float(D[pi, vi])
                if dist < settings.PROXIMITY_THRESHOLD:
                    close_pairs.append(
                        (persons[pi].track_id, vehicles[vi].track_id, dist)
                    )
        return close_pairs

    def reset(self) -> None:
        self._prev_occupancy.clear()
