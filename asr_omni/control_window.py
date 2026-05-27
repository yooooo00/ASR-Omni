from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


DEFAULT_CONTROL_WINDOW_GEOMETRY = "144x54+40+160"
CONTROL_WINDOW_POLL_MS = 200


class ControlWindowState:
    def __init__(self, app: Any) -> None:
        self.app = app

    def toggle(self) -> None:
        self.app.toggle_recording()

    def snapshot(self) -> dict[str, str | bool]:
        is_recording = getattr(self.app, "is_recording", None)
        if callable(is_recording):
            recording = bool(is_recording())
        else:
            recording = bool(getattr(self.app, "recording", False))
        return {
            "recording": recording,
            "label": "Recording" if recording else "Start",
            "background": "#b91c1c" if recording else "#1f6feb",
            "foreground": "#ffffff",
        }


def get_control_window_style(geometry: str = DEFAULT_CONTROL_WINDOW_GEOMETRY) -> dict[str, str | bool]:
    return {
        "geometry": geometry,
        "topmost": True,
    }


class FloatingControlWindow:
    def __init__(
        self,
        app: Any,
        *,
        geometry: str = DEFAULT_CONTROL_WINDOW_GEOMETRY,
        on_close: Callable[[], None] | None = None,
        poll_interval_ms: int = CONTROL_WINDOW_POLL_MS,
    ) -> None:
        self.state = ControlWindowState(app)
        self.geometry = geometry
        self.on_close = on_close
        self.poll_interval_ms = int(poll_interval_ms)
        self._stop_requested = threading.Event()

    def run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.title("ASR Omni")
        style = get_control_window_style(self.geometry)
        root.geometry(str(style["geometry"]))
        root.attributes("-topmost", bool(style["topmost"]))
        root.resizable(False, False)

        button = tk.Button(root, command=self.state.toggle, font=("Segoe UI", 11), relief=tk.FLAT)
        button.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        def close() -> None:
            if self.on_close is not None:
                self.on_close()
            root.destroy()

        def refresh() -> None:
            if self._stop_requested.is_set():
                root.destroy()
                return
            snapshot = self.state.snapshot()
            button.configure(
                text=str(snapshot["label"]),
                bg=str(snapshot["background"]),
                fg=str(snapshot["foreground"]),
                activebackground=str(snapshot["background"]),
                activeforeground=str(snapshot["foreground"]),
            )
            root.after(self.poll_interval_ms, refresh)

        root.protocol("WM_DELETE_WINDOW", close)
        refresh()
        root.mainloop()

    def stop(self) -> None:
        self._stop_requested.set()


def start_control_window(
    app: Any,
    *,
    enabled: bool,
    on_close: Callable[[], None] | None = None,
    geometry: str = DEFAULT_CONTROL_WINDOW_GEOMETRY,
) -> FloatingControlWindow | None:
    if not enabled:
        return None

    control_window = FloatingControlWindow(app, geometry=geometry, on_close=on_close)

    def run() -> None:
        try:
            control_window.run()
        except Exception as exc:
            print(f"[control] window failed: {exc}", flush=True)

    thread = threading.Thread(target=run, name="asr-control-window", daemon=True)
    thread.start()
    return control_window
