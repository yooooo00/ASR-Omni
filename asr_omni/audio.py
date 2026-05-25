from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import List, Optional

import numpy as np


def to_mono_float32(samples: np.ndarray) -> np.ndarray:
    data = np.asarray(samples, dtype=np.float32)
    if data.ndim == 0:
        return data.reshape(1)
    if data.ndim == 1:
        return data
    return np.mean(data, axis=-1).astype(np.float32).reshape(-1)


def rms(samples: np.ndarray) -> float:
    data = to_mono_float32(samples)
    if data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(data, dtype=np.float32), dtype=np.float32)))


@dataclass(frozen=True)
class SegmenterConfig:
    sample_rate: int = 16000
    silence_threshold: float = 0.015
    silence_seconds: float = 2.0
    min_segment_seconds: float = 0.8
    max_segment_seconds: float = 30.0
    preview_interval_seconds: float = 1.0
    min_preview_seconds: float = 1.0


class AudioSegmenter:
    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = 0.015,
        silence_seconds: float = 0.8,
        min_segment_seconds: float = 0.8,
        max_segment_seconds: float = 8.0,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.silence_threshold = float(silence_threshold)
        self.silence_samples = max(1, int(float(silence_seconds) * self.sample_rate))
        self.min_segment_samples = max(1, int(float(min_segment_seconds) * self.sample_rate))
        self.max_segment_samples = max(self.min_segment_samples, int(float(max_segment_seconds) * self.sample_rate))
        self._buffer = np.empty(0, dtype=np.float32)
        self._speech_started = False
        self._trailing_silence = 0

    def add(self, samples: np.ndarray) -> List[np.ndarray]:
        data = to_mono_float32(samples)
        if data.size == 0:
            return []

        emitted: List[np.ndarray] = []
        offset = 0
        while offset < data.size:
            room = self.max_segment_samples - self._buffer.size
            if room <= 0:
                emitted.append(self._emit())
                continue

            chunk = data[offset : offset + room]
            offset += chunk.size
            if chunk.size == 0:
                continue

            chunk_is_speech = rms(chunk) > self.silence_threshold
            if not self._speech_started and not chunk_is_speech:
                continue

            self._speech_started = self._speech_started or chunk_is_speech
            self._buffer = np.concatenate([self._buffer, chunk.astype(np.float32, copy=False)])
            self._trailing_silence = 0 if chunk_is_speech else self._trailing_silence + chunk.size

            if self._buffer.size >= self.max_segment_samples:
                emitted.append(self._emit())
            elif (
                self._buffer.size >= self.min_segment_samples
                and self._trailing_silence >= self.silence_samples
            ):
                emitted.append(self._emit())

        return emitted

    def flush(self) -> List[np.ndarray]:
        if self._speech_started and self._buffer.size >= self.min_segment_samples:
            return [self._emit()]
        self._reset()
        return []

    def snapshot(self, min_samples: int = 1) -> Optional[np.ndarray]:
        if not self._speech_started or self._buffer.size < int(min_samples):
            return None
        return self._buffer.astype(np.float32, copy=True)

    def _emit(self) -> np.ndarray:
        segment = self._buffer.astype(np.float32, copy=True)
        self._reset()
        return segment

    def _reset(self) -> None:
        self._buffer = np.empty(0, dtype=np.float32)
        self._speech_started = False
        self._trailing_silence = 0


class MicrophoneRecorder:
    def __init__(
        self,
        segment_queue: "queue.Queue[np.ndarray]",
        config: SegmenterConfig,
        device: Optional[int | str] = None,
        block_seconds: float = 0.2,
        preview_queue: Optional["queue.Queue[np.ndarray]"] = None,
    ) -> None:
        self.segment_queue = segment_queue
        self.preview_queue = preview_queue
        self.config = config
        self.device = device
        self.blocksize = max(1, int(config.sample_rate * block_seconds))
        self.preview_interval_samples = max(1, int(config.preview_interval_seconds * config.sample_rate))
        self.min_preview_samples = max(1, int(config.min_preview_seconds * config.sample_rate))
        self._samples_since_preview = 0
        self.segmenter = AudioSegmenter(
            sample_rate=config.sample_rate,
            silence_threshold=config.silence_threshold,
            silence_seconds=config.silence_seconds,
            min_segment_seconds=config.min_segment_seconds,
            max_segment_seconds=config.max_segment_seconds,
        )
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.blocksize,
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            stream = self._stream
            self._stream = None
        if stream is not None:
            stream.stop()
            stream.close()
        for segment in self.segmenter.flush():
            self.segment_queue.put(segment)

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            print(f"[audio] {status}", flush=True)
        data = indata.copy()
        segments = self.segmenter.add(data)
        for segment in segments:
            self.segment_queue.put(segment)
        if segments:
            self._samples_since_preview = 0
            return
        if self.preview_queue is None:
            return
        self._samples_since_preview += to_mono_float32(data).size
        if self._samples_since_preview < self.preview_interval_samples:
            return
        snapshot = self.segmenter.snapshot(self.min_preview_samples)
        if snapshot is None:
            return
        self.preview_queue.put(snapshot)
        self._samples_since_preview = 0
