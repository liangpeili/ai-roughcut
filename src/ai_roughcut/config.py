from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SilencePolicy:
    mark_after: float = 0.8
    compress_after: float = 1.5
    long_after: float = 3.0
    medium_target: float = 0.4
    long_target: float = 0.6


@dataclass(frozen=True)
class DecisionPolicy:
    auto_confidence: float = 0.85
    review_confidence: float = 0.75
    merge_gap: float = 0.3
    cut_margin: float = 0.15
    protected_speakers: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Profile:
    name: str
    silence: SilencePolicy = field(default_factory=SilencePolicy)
    decisions: DecisionPolicy = field(default_factory=DecisionPolicy)
    filler_words: tuple[str, ...] = (
        "嗯",
        "呃",
        "额",
        "啊",
        "呃呃",
        "嗯嗯",
        "那个",
        "这个",
        "就是",
        "然后然后",
        "怎么说呢",
    )


PROFILES = {
    "default": Profile(name="default"),
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {name!r}; available profiles: {available}") from exc
