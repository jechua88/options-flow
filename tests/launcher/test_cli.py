from __future__ import annotations

from option_flow.launcher.cli import build_parser, main


def test_build_parser_defaults(tmp_path):
    parser = build_parser()
    args = parser.parse_args([])
    assert args.include_ui is True
    assert args.include_ingest is True
    assert args.log_file == "logs/launcher.log"


def test_cli_main_invokes_launcher(monkeypatch, tmp_path):
    calls = {
        "start": 0,
        "wait": 0,
        "stop": 0,
    }

    class DummyLauncher:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def start(self):
            calls["start"] += 1

        def wait(self):
            calls["wait"] += 1

        def stop(self):
            calls["stop"] += 1

    monkeypatch.setattr("option_flow.launcher.cli.Launcher", DummyLauncher)
    log_file = tmp_path / "launcher.log"
    exit_code = main(["--demo", "--no-ui", "--log-file", str(log_file)])
    assert exit_code == 0
    assert calls == {"start": 1, "wait": 1, "stop": 1}
