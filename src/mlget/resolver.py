"""Package resolver (MVP).

This module provides a very small resolver which accepts:
- direct URLs (http/https/file)
- local wheel/tar paths

For the full project we will extend this to resolve PyTorch wheel URLs by parsing
version and platform tags; for MVP we keep it minimal and explicit to avoid
incorrect assumptions.
"""

from __future__ import annotations

from pathlib import Path


def is_url(spec: str) -> bool:
    return (
        spec.startswith("http://")
        or spec.startswith("https://")
        or spec.startswith("file://")
    )


def resolve(package_spec: str) -> list[str]:
    """Resolve a package spec to one or more download URLs or local paths.

    Rules (MVP):
    - If spec is a URL, return [spec]
    - If spec is a local file path (exists), return [absolute_path]
    - Otherwise raise ValueError and ask user for a direct URL or local wheel

    Returns a list of candidate URLs (strings).
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

    raise ValueError(
        "Could not resolve package spec automatically. Please provide a direct URL to the wheel or a local path."
    )


__all__ = ["resolve"]
