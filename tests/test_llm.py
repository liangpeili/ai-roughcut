from ai_roughcut.llm import build_ai_task, read_json_from_string


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
