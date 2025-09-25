from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

from option_flow.launcher.runner import Launcher


def _import_gui():  # pragma: no cover - import guarded for testability
    try:
        import PySimpleGUI as sg  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "PySimpleGUI is required for the desktop app. Install with `pip install option-flow[desktop]`."
        ) from exc
    return sg


def main() -> None:
    sg = _import_gui()

    layout = [
        [sg.Text("Option Flow Control", font=("Segoe UI", 14, "bold"))],
        [sg.Checkbox("Demo mode", key="-DEMO-", default=True)],
        [sg.Button("Start", key="-START-", size=(10, 1)), sg.Button("Stop", key="-STOP-", size=(10, 1), disabled=True), sg.Button("Open UI", key="-OPEN-", size=(10, 1))],
        [sg.Multiline("", size=(60, 12), key="-LOG-", autoscroll=True, disabled=True)],
        [sg.Button("Exit")],
    ]

    window = sg.Window("Option Flow Desktop", layout, finalize=True)
    launcher: Optional[Launcher] = None
    log_path = Path.cwd() / "logs" / "desktop-launcher.log"

    def write_log(message: str) -> None:
        current = window["-LOG-"].get()
        window["-LOG-"].update(value=f"{current}{message}\n")

    def monitor_launcher(stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            if launcher is None:
                time.sleep(0.5)
                continue
            status = launcher.status()
            window.write_event_value("-STATUS-", status)
            time.sleep(1.0)

    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_launcher, args=(stop_event,), daemon=True)
    monitor_thread.start()

    try:
        while True:
            event, values = window.read(timeout=500)
            if event in (sg.WIN_CLOSED, "Exit"):
                break
            if event == "-START-":
                if launcher is None:
                    launcher = Launcher(demo=values.get("-DEMO-", True), log_path=log_path)
                    try:
                        launcher.start()
                        write_log(f"Services started. Logging to {log_path}")
                        window["-START-"].update(disabled=True)
                        window["-STOP-"].update(disabled=False)
                    except Exception as exc:  # pragma: no cover
                        write_log(f"Failed to start: {exc}")
                        launcher = None
            elif event == "-STOP-":
                if launcher is not None:
                    launcher.stop()
                    write_log("Services stopped.")
                    launcher = None
                    window["-START-"].update(disabled=False)
                    window["-STOP-"].update(disabled=True)
            elif event == "-OPEN-":
                import webbrowser

                webbrowser.open("http://localhost:8501")
            elif event == "-STATUS-":
                status = values.get("-STATUS-", {})
                lines = [f"{name}: {state}" for name, state in status.items()]
                window["-LOG-"].update("\n".join(lines))
    finally:
        stop_event.set()
        if launcher is not None:
            launcher.stop()
        window.close()


if __name__ == "__main__":
    main()
