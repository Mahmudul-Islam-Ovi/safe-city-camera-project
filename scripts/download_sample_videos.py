"""Download free sample surveillance-style videos for testing without a CCTV camera.

Source: Intel IoT DevKit sample videos (CC BY 4.0)
https://github.com/intel-iot-devkit/sample-videos

Usage (from repository root, any Python 3.11 - no extra packages needed):

    python scripts/download_sample_videos.py            # default demo set
    python scripts/download_sample_videos.py --all      # every people-related clip
    python scripts/download_sample_videos.py --list

Files are saved to ``videos/sample/``. A copy of the main clip is stored as
``videos/sample/test.mp4`` so the documented command works:

    python -m app.video_processor --source ../videos/sample/test.mp4
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/"
TARGET_DIR = Path(__file__).resolve().parents[1] / "videos" / "sample"

# name -> what it is useful for in Safe City AI
VIDEOS: dict[str, str] = {
    "people-detection.mp4": "several people walking - detection & tracking (becomes test.mp4)",
    "face-demographics-walking-and-pause.mp4": "people walking and pausing - stationary / loitering demo",
    "worker-zone-detection.mp4": "workers in an industrial area - restricted zone demo",
    "one-by-one-person-detection.mp4": "people entering one by one - counting / zone entry",
    "store-aisle-detection.mp4": "store aisle - loitering / dwell time",
    "person-bicycle-car-detection.mp4": "street scene - multi-class detection",
}
DEFAULT_SET: tuple[str, ...] = (
    "people-detection.mp4",
    "face-demographics-walking-and-pause.mp4",
    "worker-zone-detection.mp4",
)


def download(name: str) -> Path:
    dest = TARGET_DIR / name
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {name} already exists")
        return dest
    url = BASE_URL + name
    tmp = dest.with_suffix(".part")
    print(f"  [get ] {name} ...", end="", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as fh:  # noqa: S310 - fixed https URL
        shutil.copyfileobj(response, fh)
    tmp.replace(dest)
    print(f" {dest.stat().st_size / 1_048_576:.1f} MB")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Safe City AI sample videos")
    parser.add_argument("--all", action="store_true", help="download every listed clip")
    parser.add_argument("--list", action="store_true", help="list available clips and exit")
    args = parser.parse_args()

    if args.list:
        for name, purpose in VIDEOS.items():
            print(f"{name:<45} {purpose}")
        return 0

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    names = list(VIDEOS) if args.all else list(DEFAULT_SET)
    print(f"Downloading {len(names)} clip(s) into {TARGET_DIR}")
    try:
        for name in names:
            download(name)
    except OSError as exc:
        print(f"\nERROR: download failed: {exc}\nCheck your internet connection or download manually from {BASE_URL}")
        return 1

    test_clip = TARGET_DIR / "test.mp4"
    if not test_clip.exists():
        shutil.copyfile(TARGET_DIR / "people-detection.mp4", test_clip)
        print("  [copy] people-detection.mp4 -> test.mp4")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
