from __future__ import annotations

import time


def prepare_text_for_insertion(text: str, append_space: bool = False) -> str:
    normalized = " ".join(line.strip() for line in str(text).splitlines() if line.strip())
    if normalized and append_space and not normalized.endswith(" "):
        normalized += " "
    return normalized


class ClipboardTextInserter:
    def __init__(self, restore_clipboard: bool = True, restore_delay_seconds: float = 0.8) -> None:
        self.restore_clipboard = restore_clipboard
        self.restore_delay_seconds = float(restore_delay_seconds)

    def insert(self, text: str, append_space: bool = False) -> bool:
        prepared = prepare_text_for_insertion(text, append_space=append_space)
        if not prepared:
            return False

        import keyboard
        import pyperclip

        old_text = None
        if self.restore_clipboard:
            try:
                old_text = pyperclip.paste()
            except pyperclip.PyperclipException:
                old_text = None

        pyperclip.copy(prepared)
        keyboard.send("ctrl+v")

        if self.restore_clipboard and old_text is not None:
            time.sleep(self.restore_delay_seconds)
            pyperclip.copy(old_text)
        return True
