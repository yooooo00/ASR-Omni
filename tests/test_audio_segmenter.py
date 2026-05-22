import numpy as np

from asr_omni.audio import AudioSegmenter


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
