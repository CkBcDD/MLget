"""aria2c subprocess wrapper (MVP).

This module provides a small wrapper around the aria2c executable using subprocess.
It is intentionally simple for MVP: start aria2c with --continue and --split
arguments, wait for completion, and return a result dict. The code is structured
so we can later swap to RPC-based control without touching higher layers.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import get_cache_dir


class Aria2cNotFound(Exception):
    pass


def find_aria2c() -> str | None:
    return shutil.which("aria2c")


class Aria2cDownloader:
    def __init__(self, aria2c_path: str | None = None) -> None:
        self.aria2c = aria2c_path or find_aria2c()
        if not self.aria2c:
            raise Aria2cNotFound(
                "aria2c executable not found. Please install aria2 (aria2c) and ensure it's on your PATH."
            )

    def download(
        self,
        url: str,
        out: Path | None = None,
        split: int = 8,
        extra_args: list[str] | None = None,
    ) -> dict:
        out_dir = Path(out or get_cache_dir())
        out_dir.mkdir(parents=True, exist_ok=True)

        # Determine output file name
        filename = Path(url).name or "downloaded.file"
        out_path = out_dir / filename

        # If there is a .part file, allow aria2c to continue
        part_path = out_dir / (filename + ".part")

        args = [
            self.aria2c,
            "--enable-rpc=false",
            f"--split={split}",
            f"--max-connection-per-server={split}",
            "--continue=true",
            "--dir",
            str(out_dir),
            "--out",
            filename,
            url,
        ]
        if extra_args:
            # ensure all extra args are strings and filter out None
            safe_extras = [str(a) for a in extra_args if a is not None]
            # insert extra args after executable
            args = [self.aria2c] + safe_extras + args[1:]

        # Ensure all args are str for subprocess
        args = [str(a) for a in args]

        # Run aria2c synchronously. For MVP we block; later we can run async or manage multiple tasks.
        proc = subprocess.run(args, capture_output=True, text=True)

        result = {
            "url": url,
            "out_path": str(out_path),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "continued": part_path.exists(),
        }

        return result


__all__ = ["Aria2cDownloader", "Aria2cNotFound", "find_aria2c"]


def python_fallback_download(
    url: str, out: Path | None = None, chunk_size: int = 8192
) -> dict:
    """Fallback downloader implemented with urllib (works when aria2c not available).

    Writes to a .part file then renames on success. Returns a result dict compatible
    with Aria2cDownloader.download's return shape.
    """
    import urllib.request

    out_dir = Path(out or get_cache_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(url).name or "downloaded.file"
    out_path = out_dir / filename
    part_path = out_dir / (filename + ".part")

    # attempt to stream-download
    try:
        with urllib.request.urlopen(url) as resp:
            # Some response objects (e.g., file://) don't expose getheader
            total = None
            if hasattr(resp, "getheader"):
                total_h = resp.getheader("Content-Length")
                total = int(total_h) if total_h and total_h.isdigit() else None

            # Try to use tqdm if available and we know total size
            pbar = None
            if total is not None:
                try:
                    from tqdm import tqdm

                    pbar = tqdm(total=total, unit="B", unit_scale=True, desc=filename)
                except Exception:
                    pbar = None

            with open(part_path, "wb") as f:
                downloaded = 0
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if pbar:
                        pbar.update(len(chunk))
        # rename part to final
        part_path.replace(out_path)
        if pbar:
            pbar.close()
        return {
            "url": url,
            "out_path": str(out_path),
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "continued": False,
        }
    except Exception as e:
        # on error, leave part file for potential resume
        return {
            "url": url,
            "out_path": str(part_path),
            "returncode": 2,
            "stdout": "",
            "stderr": str(e),
            "continued": part_path.exists(),
        }


__all__.extend(["python_fallback_download"])
