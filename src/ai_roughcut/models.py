from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CandidateType = Literal["silence", "filler"]
CandidateSuggestion = Literal["mark", "compress", "delete"]
DecisionAction = Literal["delete", "compress", "keep", "review"]


@dataclass(frozen=True)
class Candidate:
    type: CandidateType
    start: float
    end: float
    text: str = ""
    speaker: str | None = None
    suggestion: CandidateSuggestion = "mark"
    reason: str = ""

    @property
    def duration(self) -> float:
        return round(max(0.0, self.end - self.start), 3)

    def to_dict(self) -> dict:
        data = {
            "type": self.type,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
            "suggestion": self.suggestion,
            "reason": self.reason,
        }
        if self.text:
            data["text"] = self.text
        if self.speaker:
            data["speaker"] = self.speaker
        return data


@dataclass(frozen=True)
class Decision:
    start: float
    end: float
    action: DecisionAction
    reason: str
    confidence: float
    target_duration: float | None = None
    speaker: str | None = None
    text: str = ""

    def to_dict(self) -> dict:
        data = {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
        }
        if self.target_duration is not None:
            data["target_duration"] = round(self.target_duration, 3)
        if self.speaker:
            data["speaker"] = self.speaker
        if self.text:
            data["text"] = self.text
        return data


@dataclass(frozen=True)
class EditInterval:
    start: float
    end: float
    kind: Literal["delete"]
    reason: str

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(max(0.0, self.end - self.start), 3),
            "kind": self.kind,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class KeepInterval:
    start: float
    end: float

    def to_dict(self) -> dict:
        return {"start": round(self.start, 3), "end": round(self.end, 3)}


@dataclass(frozen=True)
class ReviewItem:
    start: float
    end: float
    reason: str
    confidence: float | None = None
    text: str = ""
    speaker: str | None = None

    def to_dict(self) -> dict:
        data = {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "reason": self.reason,
        }
        if self.confidence is not None:
            data["confidence"] = round(self.confidence, 3)
        if self.text:
            data["text"] = self.text
        if self.speaker:
            data["speaker"] = self.speaker
        return data


@dataclass(frozen=True)
class CutList:
    source: str
    keep_intervals: list[KeepInterval]
    edit_intervals: list[EditInterval] = field(default_factory=list)
    review_items: list[ReviewItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "keep_intervals": [item.to_dict() for item in self.keep_intervals],
            "edit_intervals": [item.to_dict() for item in self.edit_intervals],
            "review_items": [item.to_dict() for item in self.review_items],
        }
