"""
Generate synthetic test videos with OpenCV's VideoWriter.

Usage:
    python -m sample_videos.generate_synthetic

Output:
    sample_videos/synthetic_construction.mp4

For real construction footage, see these royalty-free sources:
  - Pexels: https://www.pexels.com/search/videos/construction%20site/
  - Pixabay: https://pixabay.com/videos/search/construction%20workers/
"""

from __future__ import annotations

import math
import os
import sys

import cv2
import numpy as np

FRAME_W, FRAME_H = 960, 540
FPS = 10
DURATION_S = 30
TOTAL_FRAMES = FPS * DURATION_S

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "synthetic_construction.mp4")


def generate() -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, FPS, (FRAME_W, FRAME_H))
    if not out.isOpened():
        print(f"Error: cannot open video writer at {OUTPUT_PATH}")
        sys.exit(1)

    print(f"Generating {TOTAL_FRAMES} frames at {FPS} FPS → {OUTPUT_PATH}")

    # worker positions
    workers = [
        {"x": 150.0, "y": 200.0},
        {"x": 350.0, "y": 300.0},
        {"x": 550.0, "y": 180.0},
    ]

    for f in range(TOTAL_FRAMES):
        frame = np.full((FRAME_H, FRAME_W, 3), (50, 45, 42), dtype=np.uint8)

        # background grid
        for gx in range(0, FRAME_W, 80):
            cv2.line(frame, (gx, 0), (gx, FRAME_H), (60, 55, 52), 1)
        for gy in range(0, FRAME_H, 80):
            cv2.line(frame, (0, gy), (FRAME_W, gy), (60, 55, 52), 1)

        # restricted zone rectangle
        cv2.rectangle(frame, (600, 200), (900, 450), (0, 0, 150), 2)

        # animate workers
        for i, w in enumerate(workers):
            angle = (f * 0.03) + i * 2.0
            cx = int(w["x"] + math.sin(angle) * 40)
            cy = int(w["y"] + math.cos(angle * 0.7) * 25)
            # body
            cv2.rectangle(frame, (cx - 15, cy - 10), (cx + 15, cy + 40), (0, 160, 0), -1)
            cv2.rectangle(frame, (cx - 15, cy - 10), (cx + 15, cy + 40), (0, 200, 0), 2)
            # head
            cv2.circle(frame, (cx, cy - 18), 8, (180, 160, 140), -1, cv2.LINE_AA)
            # hardhat
            cv2.ellipse(frame, (cx, cy - 21), (10, 5), 0, 180, 360, (0, 220, 220), -1)

        # vehicle at certain frames
        if 100 <= f <= 250:
            vx = int(900 - (f - 100) * 4)
            cv2.rectangle(frame, (vx, 310), (vx + 80, 360), (200, 120, 40), -1)
            cv2.rectangle(frame, (vx, 310), (vx + 80, 360), (255, 150, 50), 2)
            cv2.circle(frame, (vx + 12, 360), 6, (80, 80, 80), -1)
            cv2.circle(frame, (vx + 68, 360), 6, (80, 80, 80), -1)

        # HUD
        cv2.putText(
            frame, f"Frame {f}/{TOTAL_FRAMES}", (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA,
        )

        out.write(frame)

    out.release()
    print(f"Done. Wrote {TOTAL_FRAMES} frames to {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
