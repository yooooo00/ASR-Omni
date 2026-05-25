import queue

import numpy as np

from asr_omni.app import VoiceInputApp
from asr_omni.audio import SegmenterConfig
from asr_omni.glossary import Glossary, GlossaryEntry


class FakeBackend:
    loaded = True

    def __init__(self):
        self.calls = []

    def active_threads(self):
        return 1

    def transcribe_array(self, segment, sample_rate):
        self.calls.append((len(segment), sample_rate))
        if len(segment) == 9:
            return "open cloud code"
        return f"text-{len(segment)}"


class FakeRecorder:
    def __init__(self):
        self.segment_queue = queue.Queue()
        self.preview_queue = queue.Queue()
        self.config = SegmenterConfig(sample_rate=10)

    def start(self):
        pass

    def stop(self):
        pass


class FakeInserter:
    def __init__(self):
        self.inserted = []

    def insert(self, text):
        self.inserted.append(text)
        return True


def test_preview_transcription_prints_without_inserting(capsys):
    backend = FakeBackend()
    recorder = FakeRecorder()
    inserter = FakeInserter()
    app = VoiceInputApp(backend, recorder, inserter)

    app._transcribe_preview(np.ones(4, dtype=np.float32))

    captured = capsys.readouterr()
    assert "[preview] text-4" in captured.out
    assert inserter.inserted == []


def test_preview_transcription_applies_glossary(capsys):
    backend = FakeBackend()
    recorder = FakeRecorder()
    inserter = FakeInserter()
    glossary = Glossary([GlossaryEntry("cloud code", "claude code")])
    app = VoiceInputApp(backend, recorder, inserter, glossary=glossary)

    app._transcribe_preview(np.ones(9, dtype=np.float32))

    captured = capsys.readouterr()
    assert "[preview] open claude code" in captured.out


def test_final_segment_transcription_still_inserts_text():
    backend = FakeBackend()
    recorder = FakeRecorder()
    inserter = FakeInserter()
    app = VoiceInputApp(backend, recorder, inserter)

    app._transcribe_segment(np.ones(6, dtype=np.float32))

    assert inserter.inserted == ["text-6"]


def test_final_segment_transcription_applies_glossary_before_insert():
    backend = FakeBackend()
    recorder = FakeRecorder()
    inserter = FakeInserter()
    glossary = Glossary([GlossaryEntry("cloud code", "claude code")])
    app = VoiceInputApp(backend, recorder, inserter, glossary=glossary)

    app._transcribe_segment(np.ones(9, dtype=np.float32))

    assert inserter.inserted == ["open claude code"]


def test_stale_previews_can_be_dropped_after_final_segment():
    backend = FakeBackend()
    recorder = FakeRecorder()
    inserter = FakeInserter()
    app = VoiceInputApp(backend, recorder, inserter)
    recorder.preview_queue.put(np.ones(4, dtype=np.float32))
    recorder.preview_queue.put(np.ones(5, dtype=np.float32))

    app._drain_preview_queue()

    assert recorder.preview_queue.empty()
