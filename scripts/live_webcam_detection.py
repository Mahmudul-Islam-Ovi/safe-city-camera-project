#!/usr/bin/env python3
"""Live Webcam Object & Human Detector (Safe City AI)

Detects whether what's in front of your webcam is a Person (Human / মানুষ)
or Other Objects (phone, bottle, laptop, chair, backpack, etc.) in real-time.

Usage:
    python scripts/live_webcam_detection.py
    python scripts/live_webcam_detection.py --camera 0 --conf 0.40
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# Project paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MODELS_DIR = PROJECT_ROOT / "ai-engine" / "models"
SNAPSHOTS_DIR = PROJECT_ROOT / "evidence" / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Visual styling tokens
COLOR_PERSON = (0, 230, 115)       # Vibrant Emerald Green (BGR)
COLOR_OTHER = (30, 140, 255)       # Bright Coral/Orange (BGR)
COLOR_HUD_BG = (18, 22, 28)        # Dark Charcoal (BGR)
COLOR_WHITE = (255, 255, 255)
COLOR_TEXT_DIM = (180, 190, 200)
COLOR_ACCENT = (255, 200, 0)       # Cyan/Yellow accent


def draw_styled_bbox(
    frame: np.ndarray,
    box: list[int],
    label: str,
    color: tuple[int, int, int],
    is_person: bool = False,
) -> None:
    """Draw a clean, modern bounding box with corner accents and a solid label badge."""
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1

    # Main rectangle with thin border
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

    # Corner brackets for futuristic/security look
    corner_len = min(20, w // 4, h // 4)
    thick = 3
    if corner_len > 4:
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thick, cv2.LINE_AA)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thick, cv2.LINE_AA)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thick, cv2.LINE_AA)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thick, cv2.LINE_AA)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thick, cv2.LINE_AA)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thick, cv2.LINE_AA)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thick, cv2.LINE_AA)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thick, cv2.LINE_AA)

    # Label Badge
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.55
    font_thick = 1
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, font_thick)

    # Badge background
    badge_y1 = max(0, y1 - th - 12)
    badge_y2 = y1
    badge_x2 = min(frame.shape[1], x1 + tw + 14)
    cv2.rectangle(frame, (x1, badge_y1), (badge_x2, badge_y2), color, -1, cv2.LINE_AA)

    # Text inside badge (black if person for contrast, white if other)
    text_color = (0, 0, 0) if is_person else (255, 255, 255)
    cv2.putText(
        frame,
        label,
        (x1 + 6, badge_y2 - 6),
        font,
        font_scale,
        text_color,
        font_thick,
        cv2.LINE_AA,
    )


def draw_hud(
    frame: np.ndarray,
    fps: float,
    person_count: int,
    other_items: list[str],
    conf_thresh: float,
    person_only_mode: bool,
    snapshot_msg: str,
) -> None:
    """Draw top glassmorphic dashboard and bottom keyboard hints."""
    h, w = frame.shape[:2]

    # --- TOP HUD OVERLAY (Height: 75px) ---
    top_bar_height = 72
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, top_bar_height), COLOR_HUD_BG, -1)
    # Blend with 0.85 opacity for glassmorphism
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    # Bottom accent line of HUD
    cv2.line(frame, (0, top_bar_height), (w, top_bar_height), (50, 60, 75), 1, cv2.LINE_AA)

    # Title & Live indicator
    cv2.circle(frame, (18, 22), 6, (0, 0, 255), -1, cv2.LINE_AA)  # Red recording dot
    cv2.putText(frame, "LIVE WEBCAM AI", (32, 26), cv2.FONT_HERSHEY_DUPLEX, 0.60, COLOR_WHITE, 1, cv2.LINE_AA)

    fps_text = f"FPS: {fps:4.1f}"
    cv2.putText(frame, fps_text, (200, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_TEXT_DIM, 1, cv2.LINE_AA)

    mode_text = f"MODE: {'PERSON ONLY' if person_only_mode else 'ALL OBJECTS'} | CONF: {int(conf_thresh * 100)}%"
    cv2.putText(frame, mode_text, (310, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_ACCENT, 1, cv2.LINE_AA)

    # Human Detection Status Banner
    if person_count > 0:
        status_str = f"HUMAN DETECTED (MANUSH): {person_count} PERSON{'S' if person_count > 1 else ''}"
        status_color = COLOR_PERSON
    else:
        status_str = "NO HUMAN DETECTED (Scan Active...)"
        status_color = (120, 130, 140)

    cv2.putText(frame, status_str, (18, 54), cv2.FONT_HERSHEY_DUPLEX, 0.62, status_color, 2, cv2.LINE_AA)

    # Other Objects Summary
    if not person_only_mode:
        if other_items:
            other_summary = f"Other Objects ({len(other_items)}): " + ", ".join(other_items[:5])
            if len(other_items) > 5:
                other_summary += f" +{len(other_items) - 5} more"
            cv2.putText(frame, other_summary, (w - 480, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_OTHER, 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "Other: None", (w - 200, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_TEXT_DIM, 1, cv2.LINE_AA)

    # --- BOTTOM KEYBOARD SHORTCUTS BAR (Height: 30px) ---
    bot_y1 = h - 30
    cv2.rectangle(overlay, (0, bot_y1), (w, h), COLOR_HUD_BG, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.line(frame, (0, bot_y1), (w, bot_y1), (50, 60, 75), 1, cv2.LINE_AA)

    controls_text = "[Q] Quit | [S] Screenshot | [P] Person Only/All | [C] Cycle Confidence | [F] Fullscreen"
    cv2.putText(frame, controls_text, (18, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_TEXT_DIM, 1, cv2.LINE_AA)

    # Flash notification banner if snapshot was taken
    if snapshot_msg:
        sw = 420
        sh = 36
        sx1 = (w - sw) // 2
        sy1 = top_bar_height + 15
        cv2.rectangle(frame, (sx1, sy1), (sx1 + sw, sy1 + sh), (0, 180, 80), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (sx1, sy1), (sx1 + sw, sy1 + sh), COLOR_WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, snapshot_msg, (sx1 + 12, sy1 + 24), cv2.FONT_HERSHEY_DUPLEX, 0.52, COLOR_WHITE, 1, cv2.LINE_AA)


def open_webcam(preferred_index: int = 0) -> tuple[cv2.VideoCapture, int]:
    """Tries preferred index using DirectShow on Windows, then falls back across 0..3."""
    indices_to_try = [preferred_index] + [i for i in [0, 1, 2] if i != preferred_index]

    for idx in indices_to_try:
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        print(f"[AI] Attempting to open webcam index {idx}...")
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            # Configure resolution for smooth 720p or standard capture
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            print(f"[AI] Successfully opened camera index {idx} (Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})")
            return cap, idx
        cap.release()

    raise RuntimeError("Could not open any webcam. Please ensure your camera is connected and not blocked by another app.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Webcam Human & Object Detector")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--conf", type=float, default=0.40, help="Initial confidence threshold (0.1 - 0.9)")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="YOLO model file")
    args = parser.parse_args()

    # Locate model
    model_path = MODELS_DIR / args.model
    if not model_path.exists():
        # Fallback to current working directory or let ultralytics fetch
        model_path = Path(args.model)

    print("=" * 65)
    print("   SAFE CITY AI — LIVE WEBCAM OBJECT & HUMAN DETECTOR   ")
    print("=" * 65)
    print(f"[AI] Loading YOLO model: {model_path}...")
    model = YOLO(str(model_path))
    print("[AI] Model loaded successfully.")

    cap, camera_idx = open_webcam(args.camera)

    window_name = "Safe City AI — Live Webcam Detection (Person vs Other Objects)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    conf_levels = [0.30, 0.40, 0.50, 0.65]
    conf_idx = 1
    conf_thresh = conf_levels[conf_idx]

    person_only_mode = False
    is_fullscreen = False

    fps = 0.0
    frame_count = 0
    fps_timer = time.time()

    snapshot_display_until = 0.0
    snapshot_msg = ""

    last_human_state: bool | None = None

    print("\n[Controls]")
    print("  [Q] or [ESC] : Quit")
    print("  [S]          : Save Snapshot to evidence/snapshots/")
    print("  [P]          : Toggle Person-Only Mode")
    print("  [C]          : Cycle Confidence Threshold")
    print("  [F]          : Toggle Fullscreen")
    print("\nStarting live detection stream...\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                fps = frame_count / (now - fps_timer)
                frame_count = 0
                fps_timer = now

            # Run inference
            results = model.predict(
                source=frame,
                conf=conf_thresh,
                imgsz=640,
                verbose=False,
            )

            person_count = 0
            other_objects_detected: list[str] = []

            if results and len(results) > 0:
                r = results[0]
                boxes = r.boxes
                if boxes is not None and len(boxes) > 0:
                    xyxy_arr = boxes.xyxy.cpu().numpy()
                    conf_arr = boxes.conf.cpu().numpy()
                    cls_arr = boxes.cls.cpu().numpy()
                    class_names = r.names

                    for xyxy, conf, cid_raw in zip(xyxy_arr, conf_arr, cls_arr, strict=False):
                        cid = int(cid_raw)
                        cname = class_names.get(cid, "unknown")
                        conf_pct = int(conf * 100)

                        is_person = (cname == "person")

                        if is_person:
                            person_count += 1
                            label = f"PERSON / MANUSH {conf_pct}%"
                            color = COLOR_PERSON
                        else:
                            if person_only_mode:
                                continue
                            other_objects_detected.append(cname)
                            label = f"OBJECT: {cname} {conf_pct}%"
                            color = COLOR_OTHER

                        x1, y1, x2, y2 = [int(v) for v in xyxy]
                        draw_styled_bbox(frame, [x1, y1, x2, y2], label, color, is_person=is_person)

            # Console notification on state change (person enters or exits)
            has_human = (person_count > 0)
            if has_human != last_human_state:
                timestamp_str = datetime.now().strftime("%H:%M:%S")
                if has_human:
                    print(f"[{timestamp_str}] >>> [HUMAN DETECTED] Person count: {person_count}")
                else:
                    print(f"[{timestamp_str}] --- [NO HUMAN] Scene clear of people.")
                last_human_state = has_human

            # Check snapshot notification banner timeout
            active_snapshot_msg = snapshot_msg if (time.time() < snapshot_display_until) else ""

            # Draw HUD
            draw_hud(
                frame=frame,
                fps=fps,
                person_count=person_count,
                other_items=other_objects_detected,
                conf_thresh=conf_thresh,
                person_only_mode=person_only_mode,
                snapshot_msg=active_snapshot_msg,
            )

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF

            # Key handlers
            if key in [ord("q"), ord("Q"), 27]:  # 27 is ESC
                print("[AI] Quitting live webcam detector.")
                break
            elif key in [ord("s"), ord("S")]:
                # Save snapshot
                snap_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                snap_path = SNAPSHOTS_DIR / f"webcam_snapshot_{snap_time}.jpg"
                cv2.imwrite(str(snap_path), frame)
                snapshot_msg = f"Saved: {snap_path.name}"
                snapshot_display_until = time.time() + 2.5
                print(f"[AI] Snapshot saved to: {snap_path}")
            elif key in [ord("p"), ord("P")]:
                person_only_mode = not person_only_mode
                print(f"[AI] Person-only mode: {'ENABLED' if person_only_mode else 'DISABLED'}")
            elif key in [ord("c"), ord("C")]:
                conf_idx = (conf_idx + 1) % len(conf_levels)
                conf_thresh = conf_levels[conf_idx]
                print(f"[AI] Confidence threshold set to: {int(conf_thresh * 100)}%")
            elif key in [ord("f"), ord("F")]:
                is_fullscreen = not is_fullscreen
                prop = cv2.WINDOW_FULLSCREEN if is_fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, prop)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[AI] Webcam stream closed cleanly.")


if __name__ == "__main__":
    main()
