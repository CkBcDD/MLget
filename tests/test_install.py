import sys
from pathlib import Path

sys.path.insert(0, "src")

from mlget.cache import CacheDB
from mlget.downloader import python_fallback_download


def test_local_file_download(tmp_path: Path):
    # Use the fixture in tests/fixture.txt
    fixture = Path("tests/fixture.txt").resolve()
    uri = fixture.as_uri()

    # Use a temporary DB and cache dir for isolation
    db_file = tmp_path / "mlget_test.db"
    db = CacheDB(db_path=db_file)

    out_dir = tmp_path

    download_id = db.add_download(uri, str(out_dir / fixture.name), status="queued")

    res = python_fallback_download(uri, out=out_dir)
    assert res.get("returncode") == 0, f"download failed: {res.get('stderr')}"

    db.update_download(download_id, status="completed")

    out_path = res.get("out_path")
    assert out_path is not None, f"download did not produce out_path: {res}"
    db.add_cache_entry(str(out_path))

    downloads = list(db.list_downloads())
    assert any(d["status"] == "completed" for d in downloads)

    cache = list(db.list_cache())
    assert len(cache) >= 1
