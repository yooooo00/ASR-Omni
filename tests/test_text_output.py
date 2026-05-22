from asr_omni.text_output import prepare_text_for_insertion


def test_prepare_text_strips_blank_lines_and_preserves_chinese_punctuation():
    text = "\n  你好，这是一个测试。\n\n"

    assert prepare_text_for_insertion(text) == "你好，这是一个测试。"


def test_prepare_text_can_append_space_for_latin_dictation():
    text = " hello world "

    assert prepare_text_for_insertion(text, append_space=True) == "hello world "


def test_prepare_text_returns_empty_string_for_blank_text():
    assert prepare_text_for_insertion(" \n\t ") == ""
