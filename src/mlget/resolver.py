"""Package resolver (MVP).

Extends the small resolver to add a specialised PyTorch path: when the user
asks for `torch` (optionally with ==version), the resolver will attempt to
detect local GPU/CUDA and use `pip download` with the appropriate
`--find-links` (download.pytorch.org/whl/...) to fetch a compatible wheel into
the local tmp directory and then return the local wheel path.

This keeps the higher-level installer unchanged (it still receives a URL or
local path) while enabling automatic GPU selection.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import get_tmp_dir


def is_url(spec: str) -> bool:
    return (
        spec.startswith("http://")
        or spec.startswith("https://")
        or spec.startswith("file://")
    )


def _detect_nvidia_cuda() -> str | None:
    """Try to detect CUDA version via `nvidia-smi` output or environment.

    Returns a string like '12.1' or '11.8' when detected, else None.
    """
    ns = shutil.which("nvidia-smi")
    if ns:
        try:
            out = subprocess.check_output([ns], stderr=subprocess.STDOUT, text=True)
            for line in out.splitlines():
                if "CUDA Version" in line:
                    # e.g. ' | NVIDIA-SMI 535.86.10    Driver Version: 535.86.10    CUDA Version: 12.1     |'
                    parts = line.split("CUDA Version")
                    if len(parts) > 1:
                        v = parts[1].strip().strip(":").strip()
                        # keep only major.minor
                        if v:
                            return v.split()[0]
        except Exception:
            pass

    # fallback: check common env vars
    for env in ("CUDA_VERSION", "CUDA_HOME", "CUDA_ROOT"):
        val = os.environ.get(env)
        if not val:
            continue
        # CUDA_HOME may be a path; try to extract version digits
        if "." in val:
            # often CUDA_VERSION is like '11.8'
            parts = val.split(".")
            if parts and parts[0].isdigit():
                return ".".join(parts[:2])
    return None


def _cuda_to_tag(cuda_ver: str | None):
    """Map a detected CUDA version to a pytorch wheel tag like 'cu121'."""
    if not cuda_ver:
        return None
    # Normalize to major.minor
    v = cuda_ver.strip()
    # Accept forms like '12.1', '11.8'
    if v.startswith("12.1"):
        return "cu121"
    if v.startswith("12.0"):
        return "cu120"
    if v.startswith("11.8"):
        return "cu118"
    if v.startswith("11.7"):
        return "cu117"
    if v.startswith("11.6"):
        return "cu116"
    # Unknown/older -> None (fall back to cpu)
    return None


def _pip_download_to_tmp(package_spec: str, find_links: str) -> list[str]:
    """Use `python -m pip download` to fetch a wheel into tmp and return local paths.

    Returns list of file paths found in the tmp dir (may be empty on failure).
    """
    tmp = Path(get_tmp_dir()) / "resolver_pip_download"
    if tmp.exists():
        # clean up stale files but keep dir
        for f in tmp.iterdir():
            try:
                if f.is_file():
                    f.unlink()
            except Exception:
                pass
    else:
        tmp.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        package_spec,
        "--no-deps",
        "--only-binary=:all:",
        "--dest",
        str(tmp),
        "-f",
        find_links,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"pip download failed: {proc.stderr.strip()}")
    except Exception as e:
        raise ValueError(
            f"Failed to download wheel for {package_spec} from {find_links}: {e}"
        )

    # collect wheel/tar files
    found: list[str] = []
    for f in tmp.iterdir():
        if f.is_file() and (f.suffix == ".whl" or f.name.endswith(".tar.gz")):
            found.append(f.resolve().as_uri())
    return found


def _resolve_torch(package_spec: str) -> list[str]:
    """Resolve torch package by detecting GPU and using pip download to fetch a wheel.

    Accepts specs like 'torch', 'torch==2.1.0' or 'torch==2.1.0+cu121' (in which case
    the +tag is respected by pip if available).
    """
    spec = package_spec.strip()
    # Extract version part if present (e.g., 'torch==2.1.0+cu121')
    pkg = spec
    if spec.startswith("torch"):
        pkg = spec

    # If user already provided an explicit +cu tag in spec, let pip choose using default indexes
    if "+cu" in spec or "+cpu" in spec:
        # Let pip download using default (this will generally pick from PyPI or special indexes)
        # We'll still try the main pytorch cpu index as a fallback
        find_links = "https://download.pytorch.org/whl/cu121/"
        return _pip_download_to_tmp(pkg, find_links)

    # Detect GPU/CUDA
    cuda = _detect_nvidia_cuda()
    tag = _cuda_to_tag(cuda)
    if tag:
        find_links = f"https://download.pytorch.org/whl/{tag}/"
        files = _pip_download_to_tmp(pkg, find_links)
        return files
    else:
        # fallback to cpu builds
        find_links = "https://download.pytorch.org/whl/cpu/"

        files = _pip_download_to_tmp(pkg, find_links)
        return files


def resolve(package_spec: str) -> list[str]:
    """Resolve a package spec to one or more download URLs or local paths.

    Rules (MVP):
    - If spec is a URL, return [spec]
    - If spec is a local file path (exists), return [absolute_path]
    - If spec looks like torch(/pytorch), attempt special resolution: detect GPU and
      use pip download to obtain a matching wheel into the tmp dir and return its path(s).
    - Otherwise raise ValueError and ask user for a direct URL or local wheel

    Returns a list of candidate URLs (strings) or local paths.
    """
    spec = package_spec.strip()
    if is_url(spec):
        return [spec]

    p = Path(spec)
    if p.exists():
        return [str(p.resolve())]

    # Heuristic: if spec looks like a wheel filename, still return as-is (user may supply)
    if spec.endswith(".whl") or spec.endswith(".tar.gz"):
        return [spec]

    # Special-case PyTorch / torch resolution
    lower = spec.split()[0].lower()
    if lower.startswith("torch") or lower.startswith("pytorch"):
        files = _resolve_torch(spec)
        if files:
            return files
        raise ValueError(
            "Could not automatically download a matching PyTorch wheel. Please provide a direct wheel URL or local path."
        )

    raise ValueError(
        "Could not resolve package spec automatically. Please provide a direct URL to the wheel or a local path."
    )


__all__ = ["resolve"]
