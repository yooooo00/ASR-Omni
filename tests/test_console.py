from asr_omni.console import safe_console_text


def test_safe_console_text_replaces_characters_not_supported_by_console_encoding():
    text = "microphone \u00ae"

    assert safe_console_text(text, encoding="gbk") == "microphone ?"
