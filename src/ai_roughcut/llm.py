from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from .io_utils import read_json, write_json

VALID_ACTIONS = {"delete", "compress", "keep", "review"}
SYSTEM_PROMPT = "你是纪实访谈视频粗剪助手。只返回 JSON。"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"


def build_ai_task(transcript: dict, candidates: list[dict], profile_name: str) -> dict:
    return {
        "role": "documentary_interview_roughcut_assistant",
        "profile": profile_name,
        "style_rules": [
            "保留被访谈者的真实语气、方言、笑声和情绪停顿。",
            "不要把访谈剪成流畅口播课。",
            "对于候选建议为 compress 的明显长空白，优先执行 compress。",
            "对于采访者自己的重复口头禅，可以适当 delete。",
            "只有涉及隐私、学校、人名、家庭矛盾或语义不完整时才标记 review。",
            "不要过度保守：无意义的停顿和重复 filler 应该被处理。",
            "必须对 candidates 列表中的每一个候选返回一条 decision，start/end 要与候选完全一致，不要合并、不要跳过。",
        ],
        "return_format": {
            "cuts": [
                {
                    "start": 13.02,
                    "end": 13.28,
                    "action": "delete|compress|keep|review",
                    "target_duration": 0.5,
                    "reason": "判断理由",
                    "confidence": 0.91,
                }
            ]
        },
        "transcript": transcript,
        "candidates": candidates,
    }


def call_openai_compatible(task_path: Path, result_path: Path, model: str | None = None) -> dict:
    api_key = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY or OPENAI_API_KEY is required when --ai is enabled")
    client = OpenAI(api_key=api_key, base_url=os.environ.get("AI_BASE_URL", DEFAULT_BASE_URL))
    response = client.chat.completions.create(
        model=model or os.environ.get("AI_MODEL", DEFAULT_MODEL),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_path.read_text(encoding="utf-8")},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("AI model returned an empty response")
    data = read_json_from_string(content)
    write_json(result_path, data)
    return data


def read_json_from_string(content: str) -> dict:
    import json

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(stripped)


def load_ai_results(path: Path) -> list[dict]:
    data = read_json(path)
    return list(data.get("cuts", []))


def validate_ai_results(candidates: list[dict], raw_results: list[dict]) -> list[dict]:
    matched_results = {
        _candidate_key(result): result
        for result in raw_results
        if _candidate_key(result) is not None
    }
    decisions: list[dict] = []
    for candidate in candidates:
        candidate_key = _candidate_key(candidate)
        result = matched_results.get(candidate_key)
        if result is None:
            decisions.append(_review_decision(candidate, "AI 未返回该候选，转人工复查"))
            continue
        validation_error = _validation_error(result)
        if validation_error:
            decisions.append(_review_decision(candidate, validation_error))
            continue
        decisions.append(_validated_decision(candidate, result))
    return decisions


def _candidate_key(item: dict) -> tuple[float, float] | None:
    try:
        return (round(float(item["start"]), 3), round(float(item["end"]), 3))
    except (KeyError, TypeError, ValueError):
        return None


def _validation_error(result: dict) -> str:
    action = result.get("action")
    if action not in VALID_ACTIONS:
        return "AI 返回 action 非法，转人工复查"
    confidence = result.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        return "AI 返回 confidence 非法，转人工复查"
    if action == "compress" and result.get("target_duration") is None:
        return "AI compress 缺少 target_duration，转人工复查"
    if action == "compress":
        target_duration = result.get("target_duration")
        if isinstance(target_duration, bool) or not isinstance(target_duration, (int, float)) or float(target_duration) <= 0.0:
            return "AI compress 的 target_duration 非法，转人工复查"
    return ""


def _validated_decision(candidate: dict, result: dict) -> dict:
    decision = {
        "start": round(float(candidate["start"]), 3),
        "end": round(float(candidate["end"]), 3),
        "action": result["action"],
        "reason": str(result.get("reason", "")),
        "confidence": float(result["confidence"]),
    }
    if result.get("target_duration") is not None:
        decision["target_duration"] = float(result["target_duration"])
    _copy_candidate_context(candidate, decision)
    return decision


def _review_decision(candidate: dict, reason: str) -> dict:
    decision = {
        "start": round(float(candidate["start"]), 3),
        "end": round(float(candidate["end"]), 3),
        "action": "review",
        "reason": reason,
        "confidence": 0.0,
    }
    _copy_candidate_context(candidate, decision)
    return decision


def _copy_candidate_context(candidate: dict, decision: dict) -> None:
    if candidate.get("speaker"):
        decision["speaker"] = candidate["speaker"]
    if candidate.get("text"):
        decision["text"] = candidate["text"]
