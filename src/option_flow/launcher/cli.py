from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from option_flow.launcher.runner import Launcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="option-flow-launcher",
        description="Launch Option Flow API, UI, and ingest services",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode using the bundled DuckDB sample",
    )
    parser.add_argument(
        "--no-ui",
        dest="include_ui",
        action="store_false",
        help="Start without the Streamlit UI",
    )
    parser.add_argument(
        "--no-ingest",
        dest="include_ingest",
        action="store_false",
        help="Disable the ingest worker",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the Streamlit UI in a browser after launch",
    )
    parser.add_argument(
        "--log-file",
        default="logs/launcher.log",
        help="Path to write launcher log output (default: logs/launcher.log)",
    )
    parser.set_defaults(include_ui=True, include_ingest=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    launcher = Launcher(
        demo=args.demo,
        include_ui=args.include_ui,
        include_ingest=args.include_ingest,
        log_path=log_path,
    )
    try:
        launcher.start()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Failed to start services: {exc}", file=sys.stderr)
        return 1

    if args.open_browser and args.include_ui:
        webbrowser.open("http://localhost:8501")

    try:
        launcher.wait()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        launcher.stop()
        return 1
    except KeyboardInterrupt:
        launcher.stop()
    else:
        launcher.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
