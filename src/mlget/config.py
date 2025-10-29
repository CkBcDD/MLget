"""Configuration helpers for mlget (MVP).

Provides simple platform-aware locations for cache, tmp and DB.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_user_home() -> Path:
    # Cross-platform user home
    return Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())


def get_base_dir() -> Path:
    """Return base data directory for mlget, e.g. ~/.mlget or %USERPROFILE%/.mlget"""
    base = Path(os.environ.get("MLGET_HOME") or get_user_home() / ".mlget")
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_cache_dir() -> Path:
    p = get_base_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_tmp_dir() -> Path:
    p = get_base_dir() / "tmp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_db_path() -> Path:
    p = get_base_dir() / "db"
    p.mkdir(parents=True, exist_ok=True)
    return p / "mlget.db"
