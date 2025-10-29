"""Simple SQLite-backed cache and download state for mlget (MVP).

Provides a small wrapper around sqlite3 to store download tasks and cached files.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from .config import get_db_path


class CacheDB:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or get_db_path())
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                out_path TEXT,
                total_bytes INTEGER DEFAULT 0,
                downloaded_bytes INTEGER DEFAULT 0,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                pkg_name TEXT,
                pkg_version TEXT,
                size INTEGER,
                last_used_at TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def add_download(self, url: str, out_path: str, status: str = "queued") -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO downloads (url, out_path, status) VALUES (?, ?, ?)",
            (url, out_path, status),
        )
        self.conn.commit()
        # sqlite3.Cursor.lastrowid can be None in some edge cases; coerce to int
        return int(cur.lastrowid or 0)

    def update_download(self, download_id: int, **fields) -> None:
        if not fields:
            return
        keys = ",".join(f"{k} = ?" for k in fields.keys())
        vals = list(fields.values())
        vals.append(download_id)
        cur = self.conn.cursor()
        cur.execute(
            f"UPDATE downloads SET {keys}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            vals,
        )
        self.conn.commit()

    def list_downloads(self) -> Generator[dict]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, url, out_path, total_bytes, downloaded_bytes, status, created_at, updated_at FROM downloads ORDER BY created_at DESC"
        )
        cols = [c[0] for c in cur.description]
        for row in cur.fetchall():
            yield dict(zip(cols, row))

    def add_cache_entry(
        self,
        file_path: str,
        pkg_name: str | None = None,
        pkg_version: str | None = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO cache (file_path, pkg_name, pkg_version, size, last_used_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                file_path,
                pkg_name,
                pkg_version,
                Path(file_path).stat().st_size if Path(file_path).exists() else 0,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def list_cache(self) -> Generator[dict]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, file_path, pkg_name, pkg_version, size, last_used_at FROM cache ORDER BY last_used_at DESC"
        )
        cols = [c[0] for c in cur.description]
        for row in cur.fetchall():
            yield dict(zip(cols, row))


__all__ = ["CacheDB"]
