from asr_omni.text_output import ClipboardTextInserter, prepare_text_for_insertion


def test_prepare_text_strips_blank_lines_and_preserves_chinese_punctuation():
    text = "\n  你好，这是一个测试。\n\n"

    assert prepare_text_for_insertion(text) == "你好，这是一个测试。"


def test_prepare_text_can_append_space_for_latin_dictation():
    text = " hello world "

    assert prepare_text_for_insertion(text, append_space=True) == "hello world "


def test_prepare_text_returns_empty_string_for_blank_text():
    assert prepare_text_for_insertion(" \n\t ") == ""


class FakeClipboard:
    def __init__(self, old_text="old clipboard"):
        self.old_text = old_text
        self.copies = []

    def paste(self):
        return self.old_text

    def copy(self, text, *, exclude_from_history=True):
        self.copies.append((text, exclude_from_history))


class FakeKeyboard:
    def __init__(self):
        self.sent = []

    def send(self, keys):
        self.sent.append(keys)


def test_insert_excludes_transcript_and_restore_from_clipboard_history():
    clipboard = FakeClipboard(old_text="previous")
    keyboard = FakeKeyboard()
    inserter = ClipboardTextInserter(clipboard=clipboard, keyboard_module=keyboard, restore_delay_seconds=0)

    assert inserter.insert("hello") is True

    assert clipboard.copies == [("hello", True), ("previous", True)]
    assert keyboard.sent == ["ctrl+v"]


def test_insert_can_opt_in_to_clipboard_history():
    clipboard = FakeClipboard(old_text="previous")
    keyboard = FakeKeyboard()
    inserter = ClipboardTextInserter(
        clipboard=clipboard,
        keyboard_module=keyboard,
        clipboard_history=True,
        restore_delay_seconds=0,
    )

    assert inserter.insert("hello") is True

    assert clipboard.copies == [("hello", False), ("previous", False)]
