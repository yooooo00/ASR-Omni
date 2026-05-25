import numpy as np

from asr_omni.backend import QwenCpuAsrBackend


class FakeResult:
    def __init__(self, text):
        self.text = text


class FakeQwenModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio, *, context="", language=None):
        self.calls.append({"audio": audio, "context": context, "language": language})
        return [FakeResult("ok")]


def test_backend_maps_auto_language_to_qwen_auto_detection():
    backend = QwenCpuAsrBackend(
        "models/Qwen3-ASR-0.6B",
        language="auto",
        context="Mostly Chinese dictation with some English terms.",
    )
    backend.model = FakeQwenModel()

    text = backend.transcribe_array(np.ones(4, dtype=np.float32), 16000)

    assert text == "ok"
    assert backend.model.calls[0]["language"] is None
    assert backend.model.calls[0]["context"] == "Mostly Chinese dictation with some English terms."
