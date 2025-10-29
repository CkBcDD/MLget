# mlget - ML Package Manager for Unreliable Networks

MVP: multi-threaded, resumable downloads for large ML wheels (e.g., PyTorch) using aria2c as the downloader.

## Quick start

1. Ensure you have Python (3.8+) and `aria2c` installed and on PATH.

2. Install CLI runtime dependency (click):

    ```powershell
    python -m pip install click
    ```

3. Run the CLI in-place (development):

    ```powershell
    # from project root
    python -c "import sys; sys.path.insert(0,'src'); import mlget; print(mlget.__version__)"
    python -c "import sys; sys.path.insert(0,'src'); from mlget.cli import main; main(['--help'])"
    ```

## Notes

- This repository contains an MVP skeleton: CLI entry point, config helpers and placeholders for resolver/downloader/cache modules.
- aria2c is required for multi-connection resumable downloads — the project will call it as a subprocess.

## Next steps

I'll implement the resolver (PyTorch wheel URL resolution) and a simple aria2c wrapper next. Please tell me whether you prefer `tqdm` or `rich` for the console progress UI (tqdm = small dependency, rich = richer UI).
