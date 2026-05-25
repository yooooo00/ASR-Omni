import numpy as np
import queue

from asr_omni.audio import AudioSegmenter, MicrophoneRecorder, SegmenterConfig


def test_segmenter_emits_after_minimum_speech_and_trailing_silence():
    sr = 10
    segmenter = AudioSegmenter(
        sample_rate=sr,
        silence_threshold=0.01,
        silence_seconds=0.2,
        min_segment_seconds=0.3,
        max_segment_seconds=10.0,
    )

    assert segmenter.add(np.zeros(2, dtype=np.float32)) == []
    emitted = segmenter.add(np.ones(4, dtype=np.float32) * 0.2)
    assert emitted == []

    emitted = segmenter.add(np.zeros(2, dtype=np.float32))

    assert len(emitted) == 1
    assert emitted[0].dtype == np.float32
    assert emitted[0].shape == (6,)
    assert np.allclose(emitted[0][:4], 0.2)


def test_segmenter_flush_returns_pending_speech_but_ignores_pure_silence():
    sr = 10
    segmenter = AudioSegmenter(
        sample_rate=sr,
        silence_threshold=0.01,
        silence_seconds=0.2,
        min_segment_seconds=0.3,
        max_segment_seconds=10.0,
    )

    segmenter.add(np.zeros(10, dtype=np.float32))
    assert segmenter.flush() == []

    segmenter.add(np.ones(4, dtype=np.float32) * 0.2)
    flushed = segmenter.flush()

    assert len(flushed) == 1
    assert flushed[0].shape == (4,)


def test_segmenter_snapshot_returns_pending_speech_without_consuming_it():
    sr = 10
    segmenter = AudioSegmenter(
        sample_rate=sr,
        silence_threshold=0.01,
        silence_seconds=0.5,
        min_segment_seconds=0.3,
        max_segment_seconds=10.0,
    )

    segmenter.add(np.ones(4, dtype=np.float32) * 0.2)
    snapshot = segmenter.snapshot()
    flushed = segmenter.flush()

    assert snapshot is not None
    assert snapshot.shape == (4,)
    assert len(flushed) == 1
    assert flushed[0].shape == (4,)


def test_segmenter_emits_at_max_segment_length_without_waiting_for_silence():
    sr = 10
    segmenter = AudioSegmenter(
        sample_rate=sr,
        silence_threshold=0.01,
        silence_seconds=1.0,
        min_segment_seconds=0.1,
        max_segment_seconds=0.5,
    )

    emitted = segmenter.add(np.ones(6, dtype=np.float32) * 0.2)

    assert len(emitted) == 1
    assert emitted[0].shape == (5,)


def test_microphone_recorder_emits_preview_snapshots_without_final_segment():
    segment_queue = queue.Queue()
    preview_queue = queue.Queue()
    config = SegmenterConfig(
        sample_rate=10,
        silence_threshold=0.01,
        silence_seconds=1.0,
        min_segment_seconds=0.3,
        max_segment_seconds=10.0,
        preview_interval_seconds=0.4,
        min_preview_seconds=0.3,
    )
    recorder = MicrophoneRecorder(segment_queue, config, preview_queue=preview_queue)

    recorder._callback(np.ones((4, 1), dtype=np.float32) * 0.2, 4, None, None)

    assert segment_queue.empty()
    preview = preview_queue.get_nowait()
    assert preview.shape == (4,)
