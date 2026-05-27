from __future__ import annotations

import argparse
import json
import queue
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .audio import MicrophoneRecorder, SegmenterConfig
from .backend import QwenCpuAsrBackend
from .console import safe_print
from .control_window import start_control_window
from .glossary import Glossary
from .monitor import ResourceMonitor
from .text_output import ClipboardTextInserter, prepare_text_for_insertion


DEFAULT_HOTKEYS = ["ctrl+h", "alt+h"]


class VoiceInputApp:
    def __init__(
        self,
        backend: QwenCpuAsrBackend,
        recorder: MicrophoneRecorder,
        inserter: ClipboardTextInserter,
        *,
        no_paste: bool = False,
        append_space: bool = False,
        glossary: Glossary | None = None,
    ) -> None:
        self.backend = backend
        self.recorder = recorder
        self.inserter = inserter
        self.no_paste = no_paste
        self.append_space = append_space
        self.glossary = glossary or Glossary.default()
        self.segment_queue = recorder.segment_queue
        self.preview_queue = getattr(recorder, "preview_queue", None)
        self.stop_event = threading.Event()
        self.recording = False
        self._last_preview_text = ""
        self._recording_lock = threading.Lock()
        self._worker = threading.Thread(target=self._worker_loop, name="asr-worker", daemon=True)

    def start_worker(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        with self._recording_lock:
            if self.recording:
                self.recorder.stop()
                self.recording = False
        self.stop_event.set()
        self._worker.join(timeout=5)

    def toggle_recording(self) -> None:
        with self._recording_lock:
            if self.recording:
                print("[voice] stopping recording", flush=True)
                self.recorder.stop()
                self.recording = False
            else:
                print("[voice] starting recording", flush=True)
                self.recorder.start()
                self.recording = True

    def is_recording(self) -> bool:
        with self._recording_lock:
            return self.recording

    def monitor_state(self) -> dict:
        return {
            "model_loaded": self.backend.loaded,
            "queue_depth": self.segment_queue.qsize(),
            "recording": self.is_recording(),
            "active_threads": self.backend.active_threads(),
        }

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                segment = self.segment_queue.get(timeout=0.1)
            except queue.Empty:
                segment = None
            if segment is not None:
                self._last_preview_text = ""
                self._drain_preview_queue()
                self._transcribe_segment(segment)
                self.segment_queue.task_done()
                continue

            if self.preview_queue is None:
                continue
            try:
                preview = self.preview_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._transcribe_preview(preview)
            self.preview_queue.task_done()

    def _transcribe_preview(self, segment: np.ndarray) -> None:
        try:
            text = self.backend.transcribe_array(segment, self.recorder.config.sample_rate)
        except Exception as exc:
            print(f"[preview] failed: {exc}", flush=True)
            return
        prepared = self._prepare_output_text(text, append_space=False)
        if not prepared or prepared == self._last_preview_text:
            return
        self._last_preview_text = prepared
        print(f"[preview] {prepared}", flush=True)

    def _prepare_output_text(self, text: str, append_space: bool) -> str:
        prepared = prepare_text_for_insertion(text, append_space=False)
        corrected = self.glossary.apply(prepared)
        return prepare_text_for_insertion(corrected, append_space=append_space)

    def _drain_preview_queue(self) -> None:
        if self.preview_queue is None:
            return
        while True:
            try:
                self.preview_queue.get_nowait()
            except queue.Empty:
                return
            self.preview_queue.task_done()

    def _transcribe_segment(self, segment: np.ndarray) -> None:
        seconds = len(segment) / self.recorder.config.sample_rate
        print(f"[asr] transcribing {seconds:.2f}s segment", flush=True)
        started = time.perf_counter()
        try:
            text = self.backend.transcribe_array(segment, self.recorder.config.sample_rate)
        except Exception as exc:
            print(f"[asr] failed: {exc}", flush=True)
            return
        elapsed = time.perf_counter() - started
        prepared = self._prepare_output_text(text, append_space=self.append_space)
        print(f"[asr] {elapsed:.2f}s -> {prepared}", flush=True)
        if self.no_paste:
            return
        try:
            inserted = self.inserter.insert(prepared)
            print(f"[paste] {'inserted' if inserted else 'skipped empty text'}", flush=True)
        except Exception as exc:
            print(f"[paste] failed: {exc}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline Windows voice input prototype using Qwen3-ASR CPU inference.")
    parser.add_argument(
        "--config-file",
        default="settings.json",
        help="Optional local JSON settings file. Command-line arguments override file values.",
    )
    parser.add_argument("--model-dir", default="models/Qwen3-ASR-0.6B", help="Local Qwen3-ASR model directory.")
    parser.add_argument(
        "--language",
        default="auto",
        help="Qwen3-ASR language name, e.g. Chinese, English, or auto for language detection.",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Optional Qwen3-ASR context prompt for domain terms or mixed-language dictation.",
    )
    parser.add_argument("--glossary-file", default=None, help="Optional UTF-8 TSV file: source<TAB>target.")
    parser.add_argument("--no-default-glossary", action="store_true", help="Disable built-in glossary entries.")
    parser.add_argument(
        "--hotkey",
        dest="hotkeys",
        action="append",
        default=None,
        help="Global hotkey used to toggle recording. May be repeated.",
    )
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--silence-threshold", type=float, default=0.015)
    parser.add_argument("--silence-seconds", type=float, default=2.0)
    parser.add_argument("--min-segment-seconds", type=float, default=0.8)
    parser.add_argument("--max-segment-seconds", type=float, default=30.0)
    parser.add_argument(
        "--preview",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable periodic preview transcriptions while speaking. Disabled by default to reduce memory and CPU load.",
    )
    parser.add_argument("--preview-interval-seconds", type=float, default=1.0)
    parser.add_argument("--min-preview-seconds", type=float, default=1.0)
    parser.add_argument("--monitor-interval", type=float, default=2.0)
    parser.add_argument("--torch-threads", type=int, default=12)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--append-space", action="store_true", help="Append a space after each inserted segment.")
    parser.add_argument("--no-paste", action="store_true", help="Print transcripts without pasting into the active app.")
    parser.add_argument("--no-restore-clipboard", action="store_true", help="Leave transcript text in the clipboard.")
    parser.add_argument(
        "--clipboard-history",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Allow transcript clipboard writes to appear in Windows clipboard history. Disabled by default.",
    )
    parser.add_argument(
        "--control-window",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show a small always-on-top mouse control window for toggling recording.",
    )
    parser.add_argument("--input-device", default=None, help="Optional sounddevice input device id or name.")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    parser.add_argument("--test-audio", default=None, help="Transcribe one local audio file and exit.")
    return parser


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    explicit = _explicit_destinations(parser, raw_argv)
    args = parser.parse_args(raw_argv)
    config_path = Path(args.config_file)
    if config_path.exists():
        settings = _load_json_settings(config_path)
        if "hotkeys" not in explicit:
            if "hotkeys" in settings:
                args.hotkeys = normalize_hotkeys(settings["hotkeys"])
            elif "hotkey" in settings:
                args.hotkeys = normalize_hotkeys(settings["hotkey"])
        for key, value in settings.items():
            attr = key.replace("-", "_")
            if attr in {"hotkey", "hotkeys"} or attr in explicit or not hasattr(args, attr):
                continue
            setattr(args, attr, value)
    args.hotkeys = normalize_hotkeys(args.hotkeys or DEFAULT_HOTKEYS)
    args.hotkey = args.hotkeys[0]
    return args


def normalize_hotkeys(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = [value]
    elif isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        raise ValueError("hotkeys must be a string or a list of strings")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        hotkey = str(item).strip().lower()
        if not hotkey or hotkey in seen:
            continue
        normalized.append(hotkey)
        seen.add(hotkey)
    if not normalized:
        raise ValueError("At least one hotkey is required")
    return normalized


def _explicit_destinations(parser: argparse.ArgumentParser, argv: list[str]) -> set[str]:
    by_option = {}
    for action in parser._actions:
        for option in action.option_strings:
            by_option[option] = action.dest

    explicit: set[str] = set()
    for token in argv:
        if token == "--":
            break
        if not token.startswith("--"):
            continue
        option = token.split("=", 1)[0]
        dest = by_option.get(option)
        if dest:
            explicit.add(dest)
    return explicit


def _load_json_settings(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Settings file must contain a JSON object: {path}")
    return data


def list_devices() -> None:
    import sounddevice as sd

    devices = sd.query_devices()
    for index, device in enumerate(devices):
        hostapi = device.get("hostapi", "")
        name = device.get("name", "")
        inputs = int(device.get("max_input_channels", 0))
        outputs = int(device.get("max_output_channels", 0))
        rate = int(float(device.get("default_samplerate", 0) or 0))
        safe_print(f"{index}: {name} | hostapi={hostapi} | in={inputs} | out={outputs} | default_sr={rate}")


def build_glossary(args: argparse.Namespace) -> Glossary:
    glossary = Glossary([]) if args.no_default_glossary else Glossary.default()
    if args.glossary_file:
        glossary = glossary.merged(Glossary.from_tsv(Path(args.glossary_file)))
    return glossary


def register_hotkeys(keyboard_module, hotkeys: list[str], callback) -> None:
    for hotkey in hotkeys:
        keyboard_module.add_hotkey(hotkey, callback)


def build_preview_queue(args: argparse.Namespace) -> Optional["queue.Queue[np.ndarray]"]:
    if not args.preview:
        return None
    return queue.Queue(maxsize=1)


def run_test_audio(args: argparse.Namespace) -> int:
    backend = QwenCpuAsrBackend(
        Path(args.model_dir),
        language=args.language,
        context=args.context,
        max_new_tokens=args.max_new_tokens,
        torch_threads=args.torch_threads,
    )
    loaded = backend.load()
    print(f"[model] loaded in {loaded:.2f}s from {Path(args.model_dir).resolve()}", flush=True)
    started = time.perf_counter()
    text = build_glossary(args).apply(backend.transcribe_file(Path(args.test_audio)))
    print(f"[asr] {time.perf_counter() - started:.2f}s -> {text}", flush=True)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if args.list_devices:
        list_devices()
        return 0
    if args.test_audio:
        return run_test_audio(args)

    import keyboard

    segment_queue: "queue.Queue[np.ndarray]" = queue.Queue()
    backend = QwenCpuAsrBackend(
        Path(args.model_dir),
        language=args.language,
        context=args.context,
        max_new_tokens=args.max_new_tokens,
        torch_threads=args.torch_threads,
    )
    config = SegmenterConfig(
        sample_rate=args.sample_rate,
        silence_threshold=args.silence_threshold,
        silence_seconds=args.silence_seconds,
        min_segment_seconds=args.min_segment_seconds,
        max_segment_seconds=args.max_segment_seconds,
        preview_interval_seconds=args.preview_interval_seconds,
        min_preview_seconds=args.min_preview_seconds,
    )
    preview_queue = build_preview_queue(args)
    recorder = MicrophoneRecorder(segment_queue, config, device=args.input_device, preview_queue=preview_queue)
    inserter = ClipboardTextInserter(
        restore_clipboard=not args.no_restore_clipboard,
        clipboard_history=args.clipboard_history,
    )
    glossary = build_glossary(args)
    app = VoiceInputApp(
        backend,
        recorder,
        inserter,
        no_paste=args.no_paste,
        append_space=args.append_space,
        glossary=glossary,
    )
    monitor = ResourceMonitor(app.monitor_state, interval_seconds=args.monitor_interval)

    print(f"[model] loading {Path(args.model_dir).resolve()}", flush=True)
    loaded = backend.load()
    print(
        f"[model] loaded in {loaded:.2f}s; language={args.language}; hotkeys={', '.join(args.hotkeys)}",
        flush=True,
    )
    app.start_worker()
    monitor.start()

    stop_event = threading.Event()
    control_window = None

    def request_stop(signum=None, frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    register_hotkeys(keyboard, args.hotkeys, app.toggle_recording)
    control_window = start_control_window(app, enabled=args.control_window, on_close=request_stop)
    print(
        "[voice] ready. Press the hotkey or control window button to toggle recording. Press Ctrl+C in this terminal to exit.",
        flush=True,
    )
    try:
        while not stop_event.wait(0.2):
            pass
    finally:
        if control_window is not None:
            control_window.stop()
        keyboard.unhook_all_hotkeys()
        monitor.stop()
        app.stop()
        print("[voice] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
