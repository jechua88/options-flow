from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

ServiceEnv = Dict[str, str]


@dataclass
class ServiceSpec:
    name: str
    command: List[str]
    env_overrides: ServiceEnv = field(default_factory=dict)


def build_default_specs(*, demo: bool = False, include_ui: bool = True, include_ingest: bool = True) -> List[ServiceSpec]:
    """Return the default set of service specs that power the application."""

    env_api: ServiceEnv = {}
    env_ui: ServiceEnv = {"OPTION_FLOW_API_BASE": "http://localhost:8000", "STREAMLIT_SERVER_HEADLESS": "true", "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    env_ingest: ServiceEnv = {}
    if demo:
        env_api["OPTION_FLOW_DEMO_MODE"] = "true"
        env_ui["OPTION_FLOW_DEMO_MODE"] = "true"
        env_ingest["OPTION_FLOW_DEMO_MODE"] = "true"

    python = sys.executable
    specs: List[ServiceSpec] = [
        ServiceSpec(
            name="api",
            command=[
                python,
                "-m",
                "uvicorn",
                "option_flow.api.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            env_overrides=env_api,
        )
    ]

    if include_ui:
        specs.append(
            ServiceSpec(
                name="ui",
                command=[
                    python,
                    "-m",
                    "streamlit",
                    "run",
                    "src/option_flow/ui/app.py",
                    "--server.port",
                    "8501",
                ],
                env_overrides=env_ui,
            )
        )

    if include_ingest:
        specs.append(
            ServiceSpec(
                name="ingest",
                command=[python, "-m", "option_flow.ingest.worker"],
                env_overrides=env_ingest,
            )
        )

    return specs


class Launcher:
    """Coordinate lifecycle of Option Flow background services."""

    def __init__(
        self,
        *,
        demo: bool = False,
        include_ui: bool = True,
        include_ingest: bool = True,
        extra_env: ServiceEnv | None = None,
        log_path: str | Path | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        self._demo = demo
        self._include_ui = include_ui
        self._include_ingest = include_ingest
        self._extra_env = extra_env or {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._logger = logging.getLogger("option_flow.launcher")
        self._file_handler: logging.Handler | None = None
        if log_path is not None:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(path, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s")
            )
            self._logger.addHandler(handler)
            self._logger.setLevel(log_level)
            self._logger.propagate = False
            self._file_handler = handler
        elif not self._logger.handlers:
            logging.basicConfig(level=log_level)

    @property
    def processes(self) -> Dict[str, subprocess.Popen]:
        return self._processes

    def build_specs(self) -> List[ServiceSpec]:
        return build_default_specs(
            demo=self._demo,
            include_ui=self._include_ui,
            include_ingest=self._include_ingest,
        )

    def start(self) -> None:
        specs = self.build_specs()
        with self._lock:
            if self._processes:
                raise RuntimeError("Launcher already running")
            for spec in specs:
                env = os.environ.copy()
                env.update(self._extra_env)
                env.update(spec.env_overrides)
                self._logger.info("Starting service %s", spec.name)
                proc = subprocess.Popen(spec.command, env=env)
                self._processes[spec.name] = proc

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_requested.set()
        with self._lock:
            procs = list(self._processes.items())
        for name, proc in procs:
            if proc.poll() is not None:
                continue
            self._logger.info("Stopping service %s", name)
            with contextlib.suppress(Exception):
                proc.terminate()
        deadline = time.time() + timeout
        while time.time() < deadline:
            if all(proc.poll() is not None for _, proc in procs):
                break
            time.sleep(0.1)
        for name, proc in procs:
            if proc.poll() is None:
                self._logger.warning("Killing unresponsive service %s", name)
                with contextlib.suppress(Exception):
                    proc.kill()
        with self._lock:
            self._processes.clear()
        if self._file_handler is not None:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

    def wait(self) -> None:
        try:
            while not self._stop_requested.is_set():
                with self._lock:
                    procs = list(self._processes.items())
                for name, proc in procs:
                    rc = proc.poll()
                    if rc is not None:
                        self._logger.error("Service %s exited with code %s", name, rc)
                        raise RuntimeError(f"Service {name} exited with code {rc}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def status(self) -> Dict[str, str]:
        with self._lock:
            result: Dict[str, str] = {}
            for name, proc in self._processes.items():
                code = proc.poll()
                result[name] = "running" if code is None else f"exited({code})"
        return result


__all__ = ["Launcher", "ServiceSpec", "build_default_specs"]
