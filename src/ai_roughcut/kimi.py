from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from .io_utils import read_json, write_json

SYSTEM_PROMPT = "你是纪实访谈视频粗剪助手。只返回 JSON。"


def build_kimi_task(transcript: dict, candidates: list[dict], profile_name: str) -> dict:
    return {
        "role": "documentary_interview_roughcut_assistant",
        "profile": profile_name,
        "style_rules": [
            "保留真实感、方言、停顿、笑声。",
            "不要把访谈剪成流畅口播课。",
            "梁老师自己的口头禅可以适当删除。",
            "被访谈者的犹豫、沉默、情绪停顿要谨慎保留。",
            "涉及隐私、学校、人名、家庭矛盾的地方只标记为人工复查，不要自动处理。",
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


def call_kimi(task_path: Path, result_path: Path, model: str | None = None) -> dict:
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        raise RuntimeError("MOONSHOT_API_KEY is required when --kimi is enabled")
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.ai/v1")
    response = client.chat.completions.create(
        model=model or os.environ.get("KIMI_MODEL", "kimi-latest"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_path.read_text(encoding="utf-8")},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("Kimi returned an empty response")
    data = read_json_from_string(content)
    write_json(result_path, data)
    return data


def read_json_from_string(content: str) -> dict:
    import json

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(stripped)


def load_kimi_results(path: Path) -> list[dict]:
    data = read_json(path)
    return list(data.get("cuts", []))
