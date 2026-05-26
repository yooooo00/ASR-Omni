from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
NO_HISTORY_CLIPBOARD_FORMATS = (
    "ExcludeClipboardContentFromMonitorProcessing",
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
)


def prepare_text_for_insertion(text: str, append_space: bool = False) -> str:
    normalized = " ".join(line.strip() for line in str(text).splitlines() if line.strip())
    if normalized and append_space and not normalized.endswith(" "):
        normalized += " "
    return normalized


class WindowsClipboardError(RuntimeError):
    pass


def _raise_last_windows_error(message: str) -> None:
    error_code = ctypes.get_last_error()
    if error_code:
        raise WindowsClipboardError(f"{message}: {ctypes.WinError(error_code)}")
    raise WindowsClipboardError(message)


def _copy_text_to_windows_clipboard(
    text: str,
    *,
    exclude_from_history: bool = True,
    open_timeout_seconds: float = 0.5,
) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    def alloc_global(data: bytes) -> ctypes.c_void_p:
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            _raise_last_windows_error("GlobalAlloc failed")
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            _raise_last_windows_error("GlobalLock failed")
        ctypes.memmove(locked, data, len(data))
        kernel32.GlobalUnlock(handle)
        return handle

    def set_clipboard_data(format_id: int, data: bytes) -> None:
        handle = alloc_global(data)
        if not user32.SetClipboardData(format_id, handle):
            kernel32.GlobalFree(handle)
            _raise_last_windows_error(f"SetClipboardData failed for format {format_id}")

    deadline = time.monotonic() + open_timeout_seconds
    while not user32.OpenClipboard(None):
        if time.monotonic() >= deadline:
            _raise_last_windows_error("OpenClipboard failed")
        time.sleep(0.01)

    try:
        if not user32.EmptyClipboard():
            _raise_last_windows_error("EmptyClipboard failed")
        set_clipboard_data(CF_UNICODETEXT, text.encode("utf-16le") + b"\x00\x00")
        if exclude_from_history:
            for format_name in NO_HISTORY_CLIPBOARD_FORMATS:
                format_id = user32.RegisterClipboardFormatW(format_name)
                if not format_id:
                    _raise_last_windows_error(f"RegisterClipboardFormatW failed for {format_name}")
                set_clipboard_data(format_id, (0).to_bytes(4, "little"))
    finally:
        user32.CloseClipboard()


class SystemClipboard:
    def paste(self) -> str:
        import pyperclip

        return pyperclip.paste()

    def copy(self, text: str, *, exclude_from_history: bool = True) -> None:
        import pyperclip

        if os.name == "nt" and exclude_from_history:
            try:
                _copy_text_to_windows_clipboard(text, exclude_from_history=True)
                return
            except WindowsClipboardError:
                pass
        pyperclip.copy(text)


class ClipboardTextInserter:
    def __init__(
        self,
        restore_clipboard: bool = True,
        restore_delay_seconds: float = 0.8,
        clipboard_history: bool = False,
        clipboard=None,
        keyboard_module=None,
    ) -> None:
        self.restore_clipboard = restore_clipboard
        self.restore_delay_seconds = float(restore_delay_seconds)
        self.clipboard_history = bool(clipboard_history)
        self.clipboard = clipboard or SystemClipboard()
        self.keyboard_module = keyboard_module

    def insert(self, text: str, append_space: bool = False) -> bool:
        prepared = prepare_text_for_insertion(text, append_space=append_space)
        if not prepared:
            return False

        keyboard_module = self.keyboard_module
        if keyboard_module is None:
            import keyboard as keyboard_module

        old_text = None
        if self.restore_clipboard:
            try:
                old_text = self.clipboard.paste()
            except Exception:
                old_text = None

        exclude_from_history = not self.clipboard_history
        self.clipboard.copy(prepared, exclude_from_history=exclude_from_history)
        keyboard_module.send("ctrl+v")

        if self.restore_clipboard and old_text is not None:
            if self.restore_delay_seconds > 0:
                time.sleep(self.restore_delay_seconds)
            self.clipboard.copy(old_text, exclude_from_history=exclude_from_history)
        return True
