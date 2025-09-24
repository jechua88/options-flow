from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UI_APP = ROOT / "src" / "option_flow" / "ui" / "app.py"

PROCESS_SPECS = [
    [
        sys.executable,
        "-m",
        "uvicorn",
        "option_flow.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ],
    [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(UI_APP),
        "--server.port",
        "8501",
    ],
]


def main() -> None:
    procs: list[subprocess.Popen] = []
    try:
        for spec in PROCESS_SPECS:
            env = os.environ.copy()
            env.setdefault("OPTION_FLOW_API_BASE", "http://localhost:8000")
            proc = subprocess.Popen(spec, env=env)
            procs.append(proc)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            if proc.poll() is None:
                proc.wait()


if __name__ == "__main__":
    main()
