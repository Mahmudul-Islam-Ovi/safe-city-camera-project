"""CLI Video Processor for Safe City AI.

Supports running directly against:
1. Video file:   python -m app.video_processor --source ../videos/sample/test.mp4
2. Laptop webcam: python -m app.video_processor --webcam
3. RTSP stream:   python -m app.video_processor --rtsp rtsp://...

Controls:
- Press 'q' or ESC to exit.
- Press 'z' to toggle demo restricted zone.
- Press 's' to take manual evidence snapshot.
"""

from __future__ import annotations

import argparse
import sys
import time

import cv2

from app.config import get_settings
from app.pipeline.pipeline import AIPipeline
from app.utils.logger import get_logger, setup_logging
from app.video.source import FileSource, RTSPSource, VideoSource, WebcamSource

log = get_logger("video_processor")


def run_processor(source: VideoSource, display: bool = True, limit_fps: bool = True) -> None:
    settings = get_settings()
    pipeline = AIPipeline(camera_id=source.camera_id)

    log.info("Starting video processor with source: %s", source.camera_id)
    if not source.open():
        log.error("Could not open video source: %s", source.camera_id)
        return

    meta = source.metadata
    log.info("Source opened: %s (%dx%d @ %.1f FPS)", meta.source_type, meta.width, meta.height, meta.fps)

    # Initialize demo zone
    pipeline.add_demo_restricted_zone(meta.width, meta.height)

    target_interval = settings.min_frame_interval if limit_fps else 0.0
    last_inference_time = 0.0

    try:
        while True:
            ok, frame = source.read()
            if not ok or frame is None:
                log.info("End of video stream reached.")
                break

            # Frame rate limiting for laptop CPU efficiency
            now = time.time()
            if target_interval > 0 and (now - last_inference_time) < target_interval:
                time.sleep(0.005)
                continue

            last_inference_time = now
            result = pipeline.process_frame(frame, timestamp=now)

            if display:
                cv2.imshow(f"SAFE CITY AI - {source.camera_id}", result.annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):  # 'q' or ESC
                    log.info("Exit requested by operator.")
                    break
                elif key == ord("z"):
                    # Toggle zone
                    for z in pipeline.zone_manager.zones.values():
                        z.enabled = not z.enabled
                    log.info("Toggled demo zone")

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    finally:
        source.release()
        if display:
            cv2.destroyAllWindows()
        log.info("Video processor stopped.")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Safe City AI - CLI Video Analytics Processor")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--source", type=str, help="Path to MP4 video file")
    group.add_argument("--webcam", action="store_true", help="Use laptop webcam")
    group.add_argument("--rtsp", type=str, help="RTSP camera URL")

    parser.add_argument("--cam-id", type=str, default="CAM-001", help="Camera ID")
    parser.add_argument("--no-display", action="store_true", help="Headless mode without GUI window")
    args = parser.parse_args(argv)

    settings = get_settings()

    if args.webcam:
        source: VideoSource = WebcamSource(camera_index=settings.webcam_index, camera_id=args.cam_id)
    elif args.rtsp:
        source = RTSPSource(rtsp_url=args.rtsp, camera_id=args.cam_id)
    else:
        # Default to provided source or sample file test.mp4
        file_path = args.source or str(settings.resolve_path("videos/sample/test.mp4"))
        source = FileSource(file_path=file_path, camera_id=args.cam_id)

    run_processor(source, display=not args.no_display)
    return 0


if __name__ == "__main__":
    sys.exit(main())
