from __future__ import annotations

import json
from typing import Optional

import aiosqlite

from config import settings
from models import Analytics, Event, JobStatus, Severity, TimeSeriesPoint

_DB = settings.DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'queued',
                progress REAL NOT NULL DEFAULT 0.0,
                total_frames INTEGER NOT NULL DEFAULT 0,
                processed_frames INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                frame_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                track_id INTEGER,
                zone_id TEXT,
                bbox TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_job_severity ON events(job_id, severity)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id)"
        )
        await db.commit()


# ── Jobs ──────────────────────────────────────────────────────────────

async def create_job(job_id: str, total_frames: int = 0) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "INSERT INTO jobs (job_id, total_frames) VALUES (?, ?)",
            (job_id, total_frames),
        )
        await db.commit()


async def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    processed_frames: Optional[int] = None,
    total_frames: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    parts: list[str] = []
    values: list[object] = []
    if status is not None:
        parts.append("status = ?")
        values.append(status)
    if progress is not None:
        parts.append("progress = ?")
        values.append(progress)
    if processed_frames is not None:
        parts.append("processed_frames = ?")
        values.append(processed_frames)
    if total_frames is not None:
        parts.append("total_frames = ?")
        values.append(total_frames)
    if error is not None:
        parts.append("error = ?")
        values.append(error)
    if not parts:
        return
    values.append(job_id)
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            f"UPDATE jobs SET {', '.join(parts)} WHERE job_id = ?", values
        )
        await db.commit()


async def get_job(job_id: str) -> Optional[JobStatus]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            return JobStatus(
                job_id=row["job_id"],
                status=row["status"],
                progress=row["progress"],
                total_frames=row["total_frames"],
                processed_frames=row["processed_frames"],
                error=row["error"],
            )


# ── Events ────────────────────────────────────────────────────────────

async def insert_event(event: Event) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            """INSERT INTO events
               (id, job_id, timestamp, frame_number, event_type, severity, description, track_id, zone_id, bbox)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.job_id,
                event.timestamp.isoformat(),
                event.frame_number,
                event.event_type,
                event.severity.value,
                event.description,
                event.track_id,
                event.zone_id,
                json.dumps(event.bbox) if event.bbox else None,
            ),
        )
        await db.commit()


async def get_events(
    job_id: str, severity: Optional[str] = None, limit: int = 200
) -> list[Event]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        if severity:
            sql = "SELECT * FROM events WHERE job_id = ? AND severity = ? ORDER BY frame_number DESC LIMIT ?"
            params: tuple = (job_id, severity, limit)
        else:
            sql = "SELECT * FROM events WHERE job_id = ? ORDER BY frame_number DESC LIMIT ?"
            params = (job_id, limit)
        async with db.execute(sql, params) as cur:
            rows = await cur.fetchall()
            out: list[Event] = []
            for r in rows:
                bbox_val = json.loads(r["bbox"]) if r["bbox"] else None
                out.append(
                    Event(
                        id=r["id"],
                        job_id=r["job_id"],
                        timestamp=r["timestamp"],
                        frame_number=r["frame_number"],
                        event_type=r["event_type"],
                        severity=Severity(r["severity"]),
                        description=r["description"],
                        track_id=r["track_id"],
                        zone_id=r["zone_id"],
                        bbox=tuple(bbox_val) if bbox_val else None,
                    )
                )
            return out


# ── Analytics Snapshots ───────────────────────────────────────────────

async def save_analytics(job_id: str, analytics: Analytics) -> None:
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "INSERT INTO analytics_snapshots (job_id, snapshot_json) VALUES (?, ?)",
            (job_id, analytics.model_dump_json()),
        )
        await db.commit()


async def get_analytics(job_id: str) -> Optional[Analytics]:
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT snapshot_json FROM analytics_snapshots WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            return Analytics.model_validate_json(row["snapshot_json"])
