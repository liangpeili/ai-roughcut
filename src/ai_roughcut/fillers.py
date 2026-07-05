from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Candidate

PUNCTUATION_RE = re.compile(r"^[\s，。！？、,.!?;；:：\"'“”‘’（）()\[\]]+|[\s，。！？、,.!?;；:：\"'“”‘’（）()\[\]]+$")


def normalize_word(word: str) -> str:
    return PUNCTUATION_RE.sub("", word).strip()


def iter_words(transcript: dict) -> Iterable[tuple[dict, dict]]:
    for segment in transcript.get("segments", []):
        for word in segment.get("words", []):
            yield segment, word


def find_filler_candidates(transcript: dict, filler_words: Iterable[str]) -> list[Candidate]:
    fillers = set(filler_words)
    candidates: list[Candidate] = []
    for segment, word in iter_words(transcript):
        normalized = normalize_word(str(word.get("word", "")))
        if normalized not in fillers:
            continue
        start = word.get("start")
        end = word.get("end")
        if start is None or end is None:
            continue
        speaker = segment.get("speaker")
        candidates.append(
            Candidate(
                type="filler",
                start=float(start),
                end=float(end),
                text=normalized,
                speaker=str(speaker) if speaker is not None else None,
                suggestion="mark",
                reason="口头禅候选，需结合上下文判断",
            )
        )
    return candidates
