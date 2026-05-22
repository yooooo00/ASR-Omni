from asr_omni.monitor import ResourceSnapshot, format_snapshot


def test_format_snapshot_includes_memory_cpu_threads_and_model_state():
    snapshot = ResourceSnapshot(
        rss_mb=3788.4,
        system_memory_percent=64.2,
        process_cpu_percent=155.5,
        system_cpu_percent=42.0,
        thread_count=19,
        active_threads=8,
        model_loaded=True,
        queue_depth=2,
        recording=True,
    )

    text = format_snapshot(snapshot)

    assert "RSS 3788.4 MB" in text
    assert "proc CPU 155.5%" in text
    assert "sys CPU 42.0%" in text
    assert "threads 19/8" in text
    assert "queue 2" in text
    assert "recording on" in text
    assert "model loaded" in text
