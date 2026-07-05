from ai_roughcut.llm import build_ai_task, read_json_from_string, validate_ai_results


def test_build_ai_task_uses_generic_profile_and_candidates():
    task = build_ai_task(
        transcript={"segments": []},
        candidates=[{"type": "silence", "start": 1.0, "end": 2.0}],
        profile_name="default",
    )

    assert task["profile"] == "default"
    assert task["candidates"][0]["type"] == "silence"


def test_read_json_from_string_accepts_fenced_json():
    data = read_json_from_string('```json\n{"cuts": []}\n```')

    assert data == {"cuts": []}


def test_validate_ai_results_keeps_exact_candidate_matches():
    candidates = [{"type": "silence", "start": 1.0, "end": 2.0, "reason": "长空白"}]
    raw_results = [
        {
            "start": 1.0,
            "end": 2.0,
            "action": "compress",
            "target_duration": 0.5,
            "reason": "压缩停顿",
            "confidence": 0.9,
        }
    ]

    assert validate_ai_results(candidates, raw_results) == raw_results


def test_validate_ai_results_reviews_missing_and_invalid_candidates():
    candidates = [
        {"type": "silence", "start": 1.0, "end": 2.0, "reason": "长空白"},
        {"type": "filler", "start": 3.0, "end": 3.2, "text": "嗯", "reason": "口头禅"},
        {"type": "silence", "start": 5.0, "end": 6.0, "reason": "长空白"},
        {"type": "silence", "start": 7.0, "end": 8.0, "reason": "长空白"},
    ]
    raw_results = [
        {"start": 1.0, "end": 2.0, "action": "remove", "reason": "非法 action", "confidence": 0.9},
        {"start": 3.0, "end": 3.2, "action": "delete", "reason": "非法 confidence", "confidence": 1.2},
        {"start": 5.0, "end": 6.0, "action": "compress", "reason": "缺 target", "confidence": 0.9},
        {"start": 9.0, "end": 10.0, "action": "delete", "reason": "不匹配候选", "confidence": 0.9},
    ]

    decisions = validate_ai_results(candidates, raw_results)

    assert decisions == [
        {
            "start": 1.0,
            "end": 2.0,
            "action": "review",
            "reason": "AI 返回 action 非法，转人工复查",
            "confidence": 0.0,
        },
        {
            "start": 3.0,
            "end": 3.2,
            "action": "review",
            "reason": "AI 返回 confidence 非法，转人工复查",
            "confidence": 0.0,
            "text": "嗯",
        },
        {
            "start": 5.0,
            "end": 6.0,
            "action": "review",
            "reason": "AI compress 缺少 target_duration，转人工复查",
            "confidence": 0.0,
        },
        {
            "start": 7.0,
            "end": 8.0,
            "action": "review",
            "reason": "AI 未返回该候选，转人工复查",
            "confidence": 0.0,
        },
    ]
