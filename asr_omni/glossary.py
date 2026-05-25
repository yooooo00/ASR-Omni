from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class GlossaryEntry:
    source: str
    target: str


class Glossary:
    def __init__(self, entries: Iterable[GlossaryEntry] = ()) -> None:
        self.entries: List[GlossaryEntry] = [
            entry for entry in entries if entry.source.strip() and entry.target.strip()
        ]

    @classmethod
    def default(cls) -> "Glossary":
        return cls([GlossaryEntry("cloud code", "claude code")])

    @classmethod
    def from_tsv(cls, path: Path) -> "Glossary":
        entries: List[GlossaryEntry] = []
        for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid glossary line, expected source<TAB>target: {raw_line}")
            entries.append(GlossaryEntry(parts[0].strip(), parts[1].strip()))
        return cls(entries)

    def merged(self, other: "Glossary") -> "Glossary":
        return Glossary([*self.entries, *other.entries])

    def apply(self, text: str) -> str:
        corrected = str(text)
        for entry in self.entries:
            corrected = _replace_term(corrected, entry.source, entry.target)
        return corrected


def _replace_term(text: str, source: str, target: str) -> str:
    source = source.strip()
    if not source:
        return text
    pattern = re.escape(source)
    if any(ch.isascii() and ch.isalnum() for ch in source):
        pattern = rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])"
        return re.sub(pattern, target, text, flags=re.IGNORECASE)
    return text.replace(source, target)
