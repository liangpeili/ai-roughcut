from __future__ import annotations

import re

from .config import SilencePolicy
from .models import Candidate

SILENCE_START_RE = re.compile(r"silence_start:\s*(?P<start>\d+(?:\.\d+)?)")
SILENCE_END_RE = re.compile(
    r"silence_end:\s*(?P<end>\d+(?:\.\d+)?)\s*\|\s*silence_duration:\s*(?P<duration>\d+(?:\.\d+)?)"
)


def classify_silence(start: float, end: float, policy: SilencePolicy) -> Candidate | None:
    duration = end - start
    if duration < policy.mark_after:
        return None
    if duration < policy.compress_after:
        suggestion = "mark"
        reason = "短停顿，仅标记复查"
    else:
        suggestion = "compress"
        target = policy.long_target if duration >= policy.long_after else policy.medium_target
        reason = f"长空白，建议压缩到 {target:.1f} 秒"
    return Candidate(
        type="silence",
        start=start,
        end=end,
        suggestion=suggestion,
        reason=reason,
    )


def parse_ffmpeg_silencedetect(stderr: str, policy: SilencePolicy) -> list[Candidate]:
    candidates: list[Candidate] = []
    current_start: float | None = None
    for line in stderr.splitlines():
        start_match = SILENCE_START_RE.search(line)
        if start_match:
            current_start = float(start_match.group("start"))
            continue
        end_match = SILENCE_END_RE.search(line)
        if end_match and current_start is not None:
            end = float(end_match.group("end"))
            candidate = classify_silence(current_start, end, policy)
            if candidate is not None:
                candidates.append(candidate)
            current_start = None
    return candidates
