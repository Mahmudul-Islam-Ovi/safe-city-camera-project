"""Environment verification for the AI engine (Phase 1 acceptance check).

Run from the ``ai-engine`` directory::

    python -m app.utils.check_env              # dependencies, config, directories, device
    python -m app.utils.check_env --webcam     # + open the laptop webcam and grab a frame
    python -m app.utils.check_env --yolo       # + download YOLO weights and run one inference
    python -m app.utils.check_env --all        # everything

Exit code is 0 when no check FAILED (warnings are allowed), 1 otherwise.
Output uses plain ASCII so it renders in any Windows console.
"""

from __future__ import annotations

import argparse
import importlib
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Status = Literal["OK", "WARN", "FAIL"]

REQUIRED_PACKAGES: tuple[tuple[str, str], ...] = (
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
    ("ultralytics", "ultralytics"),
    ("lap", "lap"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("yaml", "PyYAML"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("redis", "redis"),
    ("httpx", "httpx"),
)


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""


@dataclass
class Report:
    results: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, status: Status, detail: str = "") -> None:
        self.results.append(CheckResult(name, status, detail))
        print(f"  [{status:^4}] {name:<34} {detail}", flush=True)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")


def _section(title: str) -> None:
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)), flush=True)


def check_python(report: Report) -> None:
    _section("Python")
    version = sys.version_info
    detail = f"{platform.python_version()} ({platform.system()} {platform.machine()})"
    report.add("Python >= 3.11", "OK" if version >= (3, 11) else "FAIL", detail)
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    report.add("Virtual environment active", "OK" if in_venv else "WARN",
               sys.prefix if in_venv else "not in a venv - recommended: ai-engine/.venv")


def check_packages(report: Report) -> bool:
    _section("Python packages")
    all_ok = True
    for module_name, pip_name in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "installed")
            report.add(pip_name, "OK", str(version))
        except Exception as exc:  # noqa: BLE001 - we want to report any import problem
            all_ok = False
            report.add(pip_name, "FAIL", f"{type(exc).__name__}: {exc}")
    return all_ok


def check_settings(report: Report) -> bool:
    _section("Configuration")
    try:
        from app.config import PROJECT_ROOT, get_settings

        settings = get_settings()
    except Exception as exc:  # noqa: BLE001
        report.add("Load settings", "FAIL", f"{type(exc).__name__}: {exc}")
        return False

    env_file = PROJECT_ROOT / ".env"
    report.add("Project root", "OK", str(PROJECT_ROOT))
    report.add(".env file", "OK" if env_file.exists() else "WARN",
               str(env_file) if env_file.exists() else "missing - copy .env.example to .env (defaults used)")
    report.add("Load settings", "OK", f"environment={settings.environment}")
    report.add("Camera / webcam index", "OK", f"{settings.default_camera_id} / {settings.webcam_index}")
    report.add("Detection model", "OK", f"{settings.yolo_model} conf>={settings.confidence_threshold}")
    report.add("Tracker", "OK", settings.tracker_type)
    report.add("Classes", "OK", ",".join(settings.detection_classes))
    report.add("Loitering", "OK",
               f"{settings.loitering_time_seconds:.0f}s within {settings.loitering_radius_pixels:.0f}px")
    report.add("Crowd thresholds", "OK",
               f"HIGH>{settings.crowd_threshold} CRITICAL>{settings.crowd_critical_threshold}")
    report.add("Privacy", "OK",
               f"face_blur={settings.face_blur_enabled} store_raw_video={settings.store_raw_video}")
    return True


def _check_writable(report: Report, label: str, path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report.add(label, "OK", str(path))
    except OSError as exc:
        report.add(label, "FAIL", f"{path}: {exc}")


def check_directories(report: Report) -> None:
    _section("Directories")
    from app.config import PROJECT_ROOT, get_settings

    settings = get_settings()
    _check_writable(report, "Models dir (writable)", settings.models_path)
    _check_writable(report, "Evidence dir (writable)", settings.evidence_path)

    sample_dir = PROJECT_ROOT / "videos" / "sample"
    videos = sorted(p.name for p in sample_dir.glob("*") if p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"})
    if videos:
        report.add("Sample videos", "OK", ", ".join(videos[:5]) + (" ..." if len(videos) > 5 else ""))
    else:
        report.add("Sample videos", "WARN", "none yet - run: python ../scripts/download_sample_videos.py")


def check_device(report: Report) -> None:
    _section("Compute device")
    try:
        import torch

        from app.config import get_settings
        from app.utils.device import describe_device, resolve_device

        settings = get_settings()
        device = resolve_device(settings.device)
        report.add("DEVICE setting", "OK", settings.device)
        report.add("Resolved device", "OK", describe_device(device))
        cuda = torch.cuda.is_available()
        report.add("CUDA available", "OK" if cuda else "WARN",
                   f"torch CUDA {torch.version.cuda}" if cuda else "no - running on CPU (fine for development)")
        report.add("CPU threads (torch)", "OK", str(torch.get_num_threads()))
    except Exception as exc:  # noqa: BLE001
        report.add("Device check", "FAIL", f"{type(exc).__name__}: {exc}")


def check_webcam(report: Report) -> None:
    _section("Webcam")
    import cv2

    from app.config import get_settings

    index = get_settings().webcam_index
    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    start = time.perf_counter()
    cap = cv2.VideoCapture(index, backend)
    try:
        if not cap.isOpened():
            report.add(f"Open webcam index {index}", "FAIL",
                       "cannot open - check camera privacy settings / other apps using it / WEBCAM_INDEX")
            return
        ok, frame = False, None
        for _ in range(10):  # first frames can be empty while the sensor warms up
            ok, frame = cap.read()
            if ok and frame is not None:
                break
            time.sleep(0.1)
        if not ok or frame is None:
            report.add(f"Read frame from index {index}", "FAIL", "camera opened but returned no frames")
            return
        height, width = frame.shape[:2]
        report.add(f"Webcam index {index}", "OK",
                   f"{width}x{height} first frame in {time.perf_counter() - start:.2f}s")
    finally:
        cap.release()


def check_yolo(report: Report) -> None:
    _section("YOLO model")
    try:
        import numpy as np
        from ultralytics import YOLO

        from app.config import get_settings
        from app.utils.device import resolve_device

        settings = get_settings()
        weights = settings.model_file(settings.yolo_model)
        weights.parent.mkdir(parents=True, exist_ok=True)

        start = time.perf_counter()
        model = YOLO(str(weights))  # auto-downloads official weights into models/ if missing
        report.add("Load weights", "OK", f"{weights.name} in {time.perf_counter() - start:.2f}s")

        device = resolve_device(settings.device)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        model.predict(frame, device=device, imgsz=settings.inference_image_size, verbose=False)  # warm-up
        start = time.perf_counter()
        runs = 5
        for _ in range(runs):
            model.predict(frame, device=device, imgsz=settings.inference_image_size, verbose=False)
        avg_ms = (time.perf_counter() - start) / runs * 1000
        report.add("Inference speed", "OK", f"{avg_ms:.1f} ms/frame (~{1000 / avg_ms:.1f} FPS) on {device}")
        names = model.names if isinstance(model.names, dict) else dict(enumerate(model.names))
        missing = [c for c in settings.detection_classes if c not in names.values()]
        report.add("Configured classes in model", "OK" if not missing else "FAIL",
                   "all present" if not missing else f"missing: {missing}")
    except Exception as exc:  # noqa: BLE001
        report.add("YOLO check", "FAIL", f"{type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe City AI - AI engine environment check")
    parser.add_argument("--webcam", action="store_true", help="also test webcam capture")
    parser.add_argument("--yolo", action="store_true", help="also download/load YOLO and benchmark")
    parser.add_argument("--all", action="store_true", help="run every check")
    args = parser.parse_args(argv)

    print("SAFE CITY AI - environment check (ai-engine)")
    report = Report()
    check_python(report)
    packages_ok = check_packages(report)
    settings_ok = check_settings(report)
    if settings_ok:
        check_directories(report)
    if packages_ok and settings_ok:
        check_device(report)
        if args.webcam or args.all:
            check_webcam(report)
        if args.yolo or args.all:
            check_yolo(report)

    print(f"\nSummary: {len(report.results)} checks, {report.failed} failed, {report.warnings} warnings")
    print("RESULT:", "PASS" if report.failed == 0 else "FAIL")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
