from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from option_flow.desktop import shortcut as shortcut_mod


class DummyShortcut:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.Targetpath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.IconLocation = ""

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("shortcut")


class DummyShell:
    def CreateShortCut(self, path: str) -> DummyShortcut:  # noqa: N802
        return DummyShortcut(path)


class DummyClient:
    def Dispatch(self, name: str) -> DummyShell:  # noqa: N802
        assert name == "WScript.Shell"
        return DummyShell()


def test_create_shortcut(monkeypatch, tmp_path):
    win32_module = SimpleNamespace(client=DummyClient())
    monkeypatch.setitem(sys.modules, "win32com", win32_module)
    monkeypatch.setitem(sys.modules, "win32com.client", win32_module.client)

    result = shortcut_mod.create_shortcut(
        name="Option Flow",
        target="python",
        arguments="-m option_flow.desktop.app",
        working_dir=str(tmp_path),
        icon=None,
        desktop_path=tmp_path,
    )
    assert result.exists()
    assert result.read_text() == "shortcut"


def test_main_handles_missing_pywin32(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "win32com", None)
    monkeypatch.setitem(sys.modules, "win32com.client", None)
    exit_code = shortcut_mod.main(["--desktop", str(Path.cwd())])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "pywin32 is required" in captured.err
