from __future__ import annotations

import sys


def safe_console_text(text: str, encoding: str | None = None) -> str:
    target_encoding = encoding or sys.stdout.encoding or "utf-8"
    return str(text).encode(target_encoding, errors="replace").decode(target_encoding, errors="replace")


def safe_print(text: str) -> None:
    print(safe_console_text(text), flush=True)
