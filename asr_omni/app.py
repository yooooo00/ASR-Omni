from __future__ import annotations

import argparse
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
from .monitor import ResourceMonitor
from .text_output import ClipboardTextInserter, prepare_text_for_insertion


class VoiceInputApp:
    def __init__(
        self,
        backend: QwenCpuAsrBackend,
        recorder: MicrophoneRecorder,
        inserter: ClipboardTextInserter,
        *,
        no_paste: bool = False,
        append_space: bool = False,
    ) -> None:
        self.backend = backend
        self.recorder = recorder
        self.inserter = inserter
        self.no_paste = no_paste
        self.append_space = append_space
        self.segment_queue = recorder.segment_queue
        self.stop_event = threading.Event()
        self.recording = False
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

    def monitor_state(self) -> dict:
        return {
            "model_loaded": self.backend.loaded,
            "queue_depth": self.segment_queue.qsize(),
            "recording": self.recording,
            "active_threads": self.backend.active_threads(),
        }

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                segment = self.segment_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self._transcribe_segment(segment)
            self.segment_queue.task_done()

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
        prepared = prepare_text_for_insertion(text, append_space=self.append_space)
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
    parser.add_argument("--model-dir", default="models/Qwen3-ASR-0.6B", help="Local Qwen3-ASR model directory.")
    parser.add_argument("--language", default="Chinese", help="Qwen3-ASR language name, e.g. Chinese or English.")
    parser.add_argument("--hotkey", default="alt+h", help="Global hotkey used to toggle recording.")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--silence-threshold", type=float, default=0.015)
    parser.add_argument("--silence-seconds", type=float, default=0.8)
    parser.add_argument("--min-segment-seconds", type=float, default=0.8)
    parser.add_argument("--max-segment-seconds", type=float, default=8.0)
    parser.add_argument("--monitor-interval", type=float, default=2.0)
    parser.add_argument("--torch-threads", type=int, default=12)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--append-space", action="store_true", help="Append a space after each inserted segment.")
    parser.add_argument("--no-paste", action="store_true", help="Print transcripts without pasting into the active app.")
    parser.add_argument("--no-restore-clipboard", action="store_true", help="Leave transcript text in the clipboard.")
    parser.add_argument("--input-device", default=None, help="Optional sounddevice input device id or name.")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    parser.add_argument("--test-audio", default=None, help="Transcribe one local audio file and exit.")
    return parser


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


def run_test_audio(args: argparse.Namespace) -> int:
    backend = QwenCpuAsrBackend(
        Path(args.model_dir),
        language=args.language,
        max_new_tokens=args.max_new_tokens,
        torch_threads=args.torch_threads,
    )
    loaded = backend.load()
    print(f"[model] loaded in {loaded:.2f}s from {Path(args.model_dir).resolve()}", flush=True)
    started = time.perf_counter()
    text = backend.transcribe_file(Path(args.test_audio))
    print(f"[asr] {time.perf_counter() - started:.2f}s -> {text}", flush=True)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
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
        max_new_tokens=args.max_new_tokens,
        torch_threads=args.torch_threads,
    )
    config = SegmenterConfig(
        sample_rate=args.sample_rate,
        silence_threshold=args.silence_threshold,
        silence_seconds=args.silence_seconds,
        min_segment_seconds=args.min_segment_seconds,
        max_segment_seconds=args.max_segment_seconds,
    )
    recorder = MicrophoneRecorder(segment_queue, config, device=args.input_device)
    inserter = ClipboardTextInserter(restore_clipboard=not args.no_restore_clipboard)
    app = VoiceInputApp(
        backend,
        recorder,
        inserter,
        no_paste=args.no_paste,
        append_space=args.append_space,
    )
    monitor = ResourceMonitor(app.monitor_state, interval_seconds=args.monitor_interval)

    print(f"[model] loading {Path(args.model_dir).resolve()}", flush=True)
    loaded = backend.load()
    print(f"[model] loaded in {loaded:.2f}s; language={args.language}; hotkey={args.hotkey}", flush=True)
    app.start_worker()
    monitor.start()

    stop_event = threading.Event()

    def request_stop(signum=None, frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    keyboard.add_hotkey(args.hotkey, app.toggle_recording)
    print("[voice] ready. Press the hotkey to toggle recording. Press Ctrl+C in this terminal to exit.", flush=True)
    try:
        while not stop_event.wait(0.2):
            pass
    finally:
        keyboard.unhook_all_hotkeys()
        monitor.stop()
        app.stop()
        print("[voice] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
