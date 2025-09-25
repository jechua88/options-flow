from __future__ import annotations

from typing import List

import pytest

from option_flow.launcher.runner import Launcher, build_default_specs


def test_build_default_specs_demo_mode():
    specs = build_default_specs(demo=True)
    names = [spec.name for spec in specs]
    assert names == ["api", "ui", "ingest"]
    ingest_spec = next(spec for spec in specs if spec.name == "ingest")
    assert ingest_spec.env_overrides["OPTION_FLOW_DEMO_MODE"].lower() == "true"


def test_launcher_start_and_stop(monkeypatch, tmp_path):
    captured: List[tuple[str, List[str], dict]] = []

    class DummyProcess:
        def __init__(self, command, env=None, **_kwargs):
            captured.append((command[0], command, env))
            self._poll = None

        def poll(self):
            return self._poll

        def terminate(self):
            self._poll = 0

        def kill(self):  # pragma: no cover - safety
            self._poll = -9

    monkeypatch.setattr("option_flow.launcher.runner.subprocess.Popen", DummyProcess)

    log_path = tmp_path / "launcher.log"
    launcher = Launcher(demo=True, log_path=log_path)
    launcher.start()
    assert set(launcher.processes.keys()) == {"api", "ui", "ingest"}
    for _, _, env in captured:
        if env is not None and "OPTION_FLOW_DEMO_MODE" in env:
            assert env["OPTION_FLOW_DEMO_MODE"].lower() == "true"
    launcher.stop()
    assert launcher.processes == {}
    assert log_path.exists()
