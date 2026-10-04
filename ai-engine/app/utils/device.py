"""Compute-device selection (CPU by default, CUDA/MPS when available)."""

from __future__ import annotations

from app.utils.logger import get_logger

log = get_logger(__name__)


def resolve_device(requested: str = "auto") -> str:
    """Translate the DEVICE setting into a device string Ultralytics/PyTorch accept.

    * ``auto``  -> ``cuda:0`` if an NVIDIA GPU is usable, else ``mps`` (Apple), else ``cpu``
    * ``cuda`` / ``cuda:N`` / ``N`` -> validated; falls back to ``cpu`` with a warning if unavailable
    * ``cpu`` / ``mps`` -> returned as-is (mps validated)

    Never raises because of missing hardware — a laptop without a GPU must still run.
    """
    import torch  # imported lazily: torch import is slow and not needed for config/tests

    requested = (requested or "auto").strip().lower()

    if requested == "cpu":
        return "cpu"

    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda:0"
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    if requested == "mps":
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "mps"
        log.warning("DEVICE=mps requested but MPS is not available; falling back to CPU")
        return "cpu"

    # cuda, cuda:N or bare index N
    index = 0
    if requested.startswith("cuda:"):
        index = int(requested.split(":", 1)[1] or 0)
    elif requested.isdigit():
        index = int(requested)

    if torch.cuda.is_available() and index < torch.cuda.device_count():
        return f"cuda:{index}"

    log.warning("DEVICE=%s requested but CUDA device is not available; falling back to CPU", requested)
    return "cpu"


def describe_device(device: str) -> str:
    """Human readable description for logs / health endpoints."""
    if device.startswith("cuda"):
        import torch

        index = int(device.split(":", 1)[1]) if ":" in device else 0
        return f"{device} ({torch.cuda.get_device_name(index)})"
    if device == "mps":
        return "mps (Apple Silicon GPU)"
    return "cpu"
