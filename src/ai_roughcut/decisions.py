from __future__ import annotations

from .config import DecisionPolicy
from .models import CutList, Decision, EditInterval, KeepInterval, ReviewItem


def normalize_decision(raw: dict) -> Decision:
    return Decision(
        start=float(raw["start"]),
        end=float(raw["end"]),
        action=raw["action"],
        reason=str(raw.get("reason", "")),
        confidence=float(raw.get("confidence", 0.0)),
        target_duration=float(raw["target_duration"]) if raw.get("target_duration") is not None else None,
        speaker=str(raw["speaker"]) if raw.get("speaker") is not None else None,
        text=str(raw.get("text", "")),
    )


def executable_edits(decisions: list[Decision], policy: DecisionPolicy) -> tuple[list[EditInterval], list[ReviewItem]]:
    edits: list[EditInterval] = []
    review_items: list[ReviewItem] = []
    for decision in decisions:
        if decision.action == "keep":
            continue
        if decision.action == "review" or decision.confidence < policy.auto_confidence:
            review_items.append(_review_item(decision, _review_reason(decision, policy)))
            continue
        if decision.speaker in policy.protected_speakers:
            review_items.append(_review_item(decision, "被保护说话人的片段，转人工复查"))
            continue
        if decision.action == "delete":
            edits.append(_delete_interval(decision.start, decision.end, policy.cut_margin, decision.reason))
        elif decision.action == "compress":
            target = decision.target_duration if decision.target_duration is not None else 0.5
            delete_start = decision.start + target
            if delete_start < decision.end:
                edits.append(_delete_interval(delete_start, decision.end, policy.cut_margin, decision.reason))
    return merge_nearby_edits(edits, policy.merge_gap), review_items


def _delete_interval(start: float, end: float, margin: float, reason: str) -> EditInterval:
    adjusted_start = round(max(0.0, start - margin), 3)
    adjusted_end = round(max(adjusted_start, end + margin), 3)
    return EditInterval(start=adjusted_start, end=adjusted_end, kind="delete", reason=reason)


def _review_reason(decision: Decision, policy: DecisionPolicy) -> str:
    if decision.action == "review":
        return decision.reason
    if decision.confidence < policy.review_confidence:
        return f"置信度 {decision.confidence:.2f} 低于人工复查阈值"
    return f"置信度 {decision.confidence:.2f} 未达到自动执行阈值"


def _review_item(decision: Decision, reason: str) -> ReviewItem:
    return ReviewItem(
        start=decision.start,
        end=decision.end,
        reason=reason,
        confidence=decision.confidence,
        text=decision.text,
        speaker=decision.speaker,
    )


def merge_nearby_edits(edits: list[EditInterval], merge_gap: float) -> list[EditInterval]:
    if not edits:
        return []
    sorted_edits = sorted(edits, key=lambda item: item.start)
    merged = [sorted_edits[0]]
    for edit in sorted_edits[1:]:
        previous = merged[-1]
        if edit.start - previous.end <= merge_gap:
            merged[-1] = EditInterval(
                start=previous.start,
                end=max(previous.end, edit.end),
                kind="delete",
                reason=f"{previous.reason}; {edit.reason}",
            )
        else:
            merged.append(edit)
    return merged


def keep_intervals(duration: float, edits: list[EditInterval]) -> list[KeepInterval]:
    intervals: list[KeepInterval] = []
    cursor = 0.0
    for edit in sorted(edits, key=lambda item: item.start):
        start = min(max(edit.start, 0.0), duration)
        end = min(max(edit.end, 0.0), duration)
        if start > cursor:
            intervals.append(KeepInterval(start=cursor, end=start))
        cursor = max(cursor, end)
    if cursor < duration:
        intervals.append(KeepInterval(start=cursor, end=duration))
    return [item for item in intervals if item.end - item.start > 0.01]


def build_cut_list(source: str, duration: float, raw_decisions: list[dict], policy: DecisionPolicy) -> CutList:
    decisions = [normalize_decision(item) for item in raw_decisions]
    edits, review_items = executable_edits(decisions, policy)
    return CutList(
        source=source,
        edit_intervals=edits,
        keep_intervals=keep_intervals(duration, edits),
        review_items=review_items,
    )
