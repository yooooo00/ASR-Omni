from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import psutil


@dataclass(frozen=True)
class ResourceSnapshot:
    rss_mb: float
    system_memory_percent: float
    process_cpu_percent: float
    system_cpu_percent: float
    thread_count: int
    active_threads: int
    model_loaded: bool
    queue_depth: int
    recording: bool
    process_cpu_cores: Optional[float] = None


def format_snapshot(snapshot: ResourceSnapshot) -> str:
    cores = snapshot.process_cpu_cores
    if cores is None:
        cores = snapshot.process_cpu_percent / 100.0
    recording = "on" if snapshot.recording else "off"
    model = "loaded" if snapshot.model_loaded else "loading"
    return (
        "[monitor] "
        f"RSS {snapshot.rss_mb:.1f} MB | "
        f"mem {snapshot.system_memory_percent:.1f}% | "
        f"proc CPU {snapshot.process_cpu_percent:.1f}% | "
        f"cores {cores:.2f} | "
        f"sys CPU {snapshot.system_cpu_percent:.1f}% | "
        f"threads {snapshot.thread_count}/{snapshot.active_threads} | "
        f"queue {snapshot.queue_depth} | "
        f"recording {recording} | "
        f"model {model}"
    )


def snapshot_process(
    process: psutil.Process,
    *,
    model_loaded: bool,
    queue_depth: int,
    recording: bool,
    active_threads: int,
) -> ResourceSnapshot:
    memory = process.memory_info()
    process_cpu = process.cpu_percent(interval=None)
    return ResourceSnapshot(
        rss_mb=memory.rss / 1024 / 1024,
        system_memory_percent=psutil.virtual_memory().percent,
        process_cpu_percent=process_cpu,
        system_cpu_percent=psutil.cpu_percent(interval=None),
        thread_count=process.num_threads(),
        active_threads=active_threads,
        model_loaded=model_loaded,
        queue_depth=queue_depth,
        recording=recording,
        process_cpu_cores=process_cpu / 100.0,
    )


class ResourceMonitor:
    def __init__(
        self,
        state_provider: Callable[[], dict],
        interval_seconds: float = 2.0,
    ) -> None:
        self.state_provider = state_provider
        self.interval_seconds = float(interval_seconds)
        self.process = psutil.Process()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self.process.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._run, name="resource-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            state = self.state_provider()
            snapshot = snapshot_process(self.process, **state)
            print(format_snapshot(snapshot), flush=True)
