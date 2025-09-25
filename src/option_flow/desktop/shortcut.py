from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_pywin32():
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pywin32 is required to create Windows shortcuts. Install with `pip install option-flow[desktop]`."
        ) from exc
    return win32com.client  # type: ignore[name-defined]


def create_shortcut(
    *,
    name: str,
    target: str,
    arguments: str = "",
    working_dir: str | None = None,
    icon: str | None = None,
    desktop_path: Path | None = None,
) -> Path:
    """Create a Windows shortcut (.lnk) on the user's desktop."""

    win32_client = _ensure_pywin32()
    desktop_dir = desktop_path or Path.home() / "Desktop"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop_dir / f"{name}.lnk"

    shell = win32_client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(target)
    if arguments:
        shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_dir or str(Path(target).parent)
    if icon:
        shortcut.IconLocation = icon
    shortcut.save()
    return shortcut_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a desktop shortcut for Option Flow")
    parser.add_argument("--name", default="Option Flow", help="Shortcut display name")
    parser.add_argument(
        "--target",
        default=str(sys.executable),
        help="Executable path the shortcut should launch",
    )
    parser.add_argument(
        "--arguments",
        default="-m option_flow.desktop.app",
        help="Command-line arguments passed to the target",
    )
    parser.add_argument("--working-dir", default=str(Path.cwd()), help="Working directory for the shortcut")
    parser.add_argument("--icon", default="", help="Optional icon file path (.ico)")
    parser.add_argument(
        "--desktop",
        default=str(Path.home() / "Desktop"),
        help="Desktop directory where the shortcut will be written",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    icon = args.icon if args.icon else None
    try:
        path = create_shortcut(
            name=args.name,
            target=args.target,
            arguments=args.arguments,
            working_dir=args.working_dir,
            icon=icon,
            desktop_path=Path(args.desktop),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Shortcut created at {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
