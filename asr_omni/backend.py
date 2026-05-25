from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import numpy as np


class QwenCpuAsrBackend:
    def __init__(
        self,
        model_dir: Path,
        *,
        language: Optional[str] = "auto",
        context: str = "",
        max_new_tokens: int = 128,
        torch_threads: Optional[int] = 12,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.language = language
        self.context = context
        self.max_new_tokens = int(max_new_tokens)
        self.torch_threads = torch_threads
        self.model = None

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def load(self) -> float:
        if self.model is not None:
            return 0.0
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")

        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")

        import torch
        from qwen_asr import Qwen3ASRModel

        if self.torch_threads:
            torch.set_num_threads(int(self.torch_threads))

        start = time.perf_counter()
        self.model = Qwen3ASRModel.from_pretrained(
            str(self.model_dir.resolve()),
            device_map="cpu",
            dtype=torch.float32,
            max_inference_batch_size=1,
            max_new_tokens=self.max_new_tokens,
        )
        return time.perf_counter() - start

    def active_threads(self) -> int:
        try:
            import torch

            return int(torch.get_num_threads())
        except Exception:
            return int(self.torch_threads or 0)

    def transcribe_array(self, samples: np.ndarray, sample_rate: int) -> str:
        if self.model is None:
            raise RuntimeError("ASR backend is not loaded")
        result = self.model.transcribe(
            (samples.astype(np.float32, copy=False), int(sample_rate)),
            context=self.context,
            language=self._qwen_language(),
        )[0]
        return result.text

    def transcribe_file(self, path: Path) -> str:
        if self.model is None:
            raise RuntimeError("ASR backend is not loaded")
        result = self.model.transcribe(
            str(Path(path).resolve()),
            context=self.context,
            language=self._qwen_language(),
        )[0]
        return result.text

    def _qwen_language(self) -> Optional[str]:
        if self.language is None:
            return None
        value = str(self.language).strip()
        if not value or value.lower() in {"auto", "none", "detect", "mixed", "zh-en", "zh+en"}:
            return None
        return value
