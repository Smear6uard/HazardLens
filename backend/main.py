from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import database as db
from config import settings
from demo_data import generate_demo_data
from models import (
    Analytics,
    Event,
    FrameResult,
    JobStatus,
    SettingsUpdate,
    ZoneConfig,
)
from pipeline import Pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App state ──────────────────────────────────────────────────────────

pipeline = Pipeline()

# Store video file paths for on-the-fly processing during SSE streaming
_job_paths: dict[str, str] = {}

# demo data cache (lazy-loaded)
_demo_cache: dict[str, object] = {}


def _get_demo() -> tuple[list[FrameResult], list[Event], Analytics]:
    if "data" not in _demo_cache:
        logger.info("Generating demo data (500 frames)...")
        frames, events, analytics = generate_demo_data()
        _demo_cache["data"] = (frames, events, analytics)
        logger.info("Demo data ready.")
    return _demo_cache["data"]  # type: ignore[return-value]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(
        "HazardLens backend started. YOLO available: %s",
        pipeline.detector.is_available(),
    )
    yield


app = FastAPI(
    title="HazardLens",
    description="Construction site safety monitoring API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Video upload ──────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_video(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    job_id = uuid.uuid4().hex[:12]
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}{ext}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Extract metadata
    cap = cv2.VideoCapture(save_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    await db.create_job(job_id)
    await db.update_job(job_id, total_frames=total, status="ready")
    _job_paths[job_id] = save_path

    logger.info("Upload %s: %d frames, saved to %s", job_id, total, save_path)
    return {"job_id": job_id, "status": "ready"}


# ── Job status ────────────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/status")
async def job_status(job_id: str):
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ── SSE stream — processes frames on-the-fly ─────────────────────────

@app.get("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str):
    video_path = _job_paths.get(job_id)
    if not video_path:
        job = await db.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        raise HTTPException(400, "Video file not available for streaming")

    async def event_generator():
        # Reset pipeline state (keeps zones intact)
        pipeline.reset()
        await db.update_job(job_id, status="processing")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            yield f"event: error\ndata: {json.dumps({'error': 'Cannot open video'})}\n\n"
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = 1.0 / settings.STREAM_FPS
        frame_idx = 0
        all_events: list[Event] = []
        analytics_interval = 30

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1

                # Process frame with CURRENT pipeline state (zones, settings)
                result = await asyncio.to_thread(
                    pipeline.process_frame, frame, job_id
                )

                # Stream annotated frame
                data = json.dumps({
                    "frame_number": result.frame_number,
                    "risk_score": result.risk_score,
                    "compliance_rate": result.compliance_rate,
                    "tracked_objects": len(result.tracked_objects),
                    "detections": len(result.detections),
                    "annotated_frame_b64": result.annotated_frame_b64,
                })
                yield f"event: frame\ndata: {data}\n\n"

                # Stream events for this frame
                for ev in result.events:
                    all_events.append(ev)
                    yield f"event: alert\ndata: {ev.model_dump_json()}\n\n"

                # Periodic analytics
                if frame_idx % analytics_interval == 0:
                    try:
                        analytics = pipeline.get_analytics()
                        yield f"event: analytics\ndata: {json.dumps(analytics.model_dump(), default=str)}\n\n"
                    except Exception:
                        pass

                # Pace output to target stream FPS
                await asyncio.sleep(frame_interval)

            # Final analytics
            try:
                analytics = pipeline.get_analytics()
                yield f"event: analytics\ndata: {json.dumps(analytics.model_dump(), default=str)}\n\n"
                await db.save_analytics(job_id, analytics)
            except Exception:
                pass

            # Save events to DB
            for ev in all_events:
                try:
                    await db.insert_event(ev)
                except Exception:
                    pass

            await db.update_job(
                job_id, status="complete", progress=1.0, processed_frames=frame_idx
            )
            yield "event: complete\ndata: {}\n\n"
            logger.info("Stream %s complete: %d frames", job_id, frame_idx)

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled for job %s at frame %d", job_id, frame_idx)
        except Exception as exc:
            logger.exception("SSE stream error for job %s: %s", job_id, exc)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            cap.release()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Analytics & events ────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/analytics")
async def job_analytics(job_id: str):
    analytics = await db.get_analytics(job_id)
    if not analytics:
        # try live analytics from pipeline
        try:
            return pipeline.get_analytics()
        except Exception:
            raise HTTPException(404, "Analytics not found")
    return analytics


@app.get("/api/jobs/{job_id}/events")
async def job_events(
    job_id: str,
    severity: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    events = await db.get_events(job_id, severity=severity, limit=limit)
    return events


# ── Zone CRUD ─────────────────────────────────────────────────────────

@app.post("/api/zones")
async def create_zone(zone: ZoneConfig):
    pipeline.zone_engine.add_zone(zone)
    return {"id": zone.id, "status": "created"}


@app.get("/api/zones")
async def list_zones():
    return list(pipeline.zone_engine.zones.values())


@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: str):
    removed = pipeline.zone_engine.remove_zone(zone_id)
    if not removed:
        raise HTTPException(404, "Zone not found")
    return {"status": "deleted"}


# ── Settings ──────────────────────────────────────────────────────────

@app.put("/api/settings")
async def update_settings(update: SettingsUpdate):
    if update.confidence_threshold is not None:
        settings.CONFIDENCE_THRESHOLD = update.confidence_threshold
    if update.skip_frames is not None:
        settings.SKIP_FRAMES = update.skip_frames
    if update.proximity_threshold is not None:
        settings.PROXIMITY_THRESHOLD = update.proximity_threshold
    if update.loiter_seconds is not None:
        settings.LOITER_SECONDS = update.loiter_seconds
    if update.stream_fps is not None:
        settings.STREAM_FPS = update.stream_fps
    return {"status": "updated"}


# ── WebSocket live processing ─────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws.accept()
    pipeline.reset()
    logger.info("WebSocket live session started")
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            b64_frame = payload.get("frame", "")

            import base64

            img_bytes = base64.b64decode(b64_frame)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                await ws.send_json({"error": "Invalid frame"})
                continue

            result = pipeline.process_frame(frame, job_id="live")
            await ws.send_json({
                "frame_number": result.frame_number,
                "risk_score": result.risk_score,
                "compliance_rate": result.compliance_rate,
                "events": [e.model_dump() for e in result.events],
                "tracked_objects": len(result.tracked_objects),
                "annotated_frame_b64": result.annotated_frame_b64,
            })
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


# ── Demo endpoints (no model needed) ─────────────────────────────────

@app.get("/api/demo/stream")
async def demo_stream():
    frames, events, analytics = _get_demo()

    async def event_generator():
        event_idx = 0
        for i, fr in enumerate(frames):
            data = json.dumps({
                "frame_number": fr.frame_number,
                "risk_score": fr.risk_score,
                "compliance_rate": fr.compliance_rate,
                "tracked_objects": len(fr.tracked_objects),
                "detections": len(fr.detections),
                "annotated_frame_b64": fr.annotated_frame_b64,
            })
            yield f"event: frame\ndata: {data}\n\n"

            while event_idx < len(events) and events[event_idx].frame_number <= fr.frame_number:
                yield f"event: alert\ndata: {events[event_idx].model_dump_json()}\n\n"
                event_idx += 1

            if (i + 1) % 30 == 0:
                yield f"event: analytics\ndata: {json.dumps(analytics.model_dump(), default=str)}\n\n"

            await asyncio.sleep(1.0 / settings.DEMO_FPS)

        yield f"event: analytics\ndata: {json.dumps(analytics.model_dump(), default=str)}\n\n"
        yield "event: complete\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/demo/analytics")
async def demo_analytics():
    _, _, analytics = _get_demo()
    return analytics


@app.get("/api/demo/events")
async def demo_events(
    severity: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    _, events, _ = _get_demo()
    if severity:
        events = [e for e in events if e.severity.value == severity]
    return events[:limit]


# ── Health ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model_available": pipeline.detector.is_available(),
        "model_name": settings.MODEL_NAME,
    }
