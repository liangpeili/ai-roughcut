from ai_roughcut.config import DecisionPolicy
from ai_roughcut.decisions import build_cut_list, executable_edits, keep_intervals, normalize_decision
from ai_roughcut.models import EditInterval


def test_delete_decision_becomes_edit_interval_with_margin():
    policy = DecisionPolicy(cut_margin=0.1)
    decision = normalize_decision(
        {
            "start": 13.02,
            "end": 13.28,
            "action": "delete",
            "reason": "梁老师口头填充词",
            "confidence": 0.91,
        }
    )

    edits, reviews = executable_edits([decision], policy)

    assert reviews == []
    assert len(edits) == 1
    assert edits[0].start == 12.92
    assert edits[0].end == 13.38


def test_compress_decision_deletes_tail_after_target_duration():
    policy = DecisionPolicy(cut_margin=0.0)
    decision = normalize_decision(
        {
            "start": 42.1,
            "end": 44.8,
            "action": "compress",
            "target_duration": 0.5,
            "reason": "保留思考感",
            "confidence": 0.9,
        }
    )

    edits, reviews = executable_edits([decision], policy)

    assert reviews == []
    assert edits[0].start == 42.6
    assert edits[0].end == 44.8


def test_lower_confidence_decision_moves_to_review():
    policy = DecisionPolicy(auto_confidence=0.85)
    decision = normalize_decision(
        {
            "start": 42.1,
            "end": 44.8,
            "action": "compress",
            "target_duration": 0.5,
            "reason": "长空白",
            "confidence": 0.8,
        }
    )

    edits, reviews = executable_edits([decision], policy)

    assert edits == []
    assert len(reviews) == 1
    assert "未达到自动执行阈值" in reviews[0].reason


def test_keep_intervals_are_inverse_of_edits():
    edits = [
        EditInterval(start=2.0, end=3.0, kind="delete", reason="a"),
        EditInterval(start=5.0, end=6.0, kind="delete", reason="b"),
    ]

    intervals = keep_intervals(8.0, edits)

    assert [item.to_dict() for item in intervals] == [
        {"start": 0.0, "end": 2.0},
        {"start": 3.0, "end": 5.0},
        {"start": 6.0, "end": 8.0},
    ]


def test_build_cut_list_merges_nearby_edits():
    policy = DecisionPolicy(cut_margin=0.0, merge_gap=0.3)
    raw_decisions = [
        {"start": 1.0, "end": 1.2, "action": "delete", "reason": "a", "confidence": 0.9},
        {"start": 1.45, "end": 1.6, "action": "delete", "reason": "b", "confidence": 0.9},
    ]

    cut_list = build_cut_list("work/00_normalized.mp4", 3.0, raw_decisions, policy)

    assert len(cut_list.edit_intervals) == 1
    assert cut_list.keep_intervals[0].to_dict() == {"start": 0.0, "end": 1.0}
    assert cut_list.keep_intervals[1].to_dict() == {"start": 1.6, "end": 3.0}
