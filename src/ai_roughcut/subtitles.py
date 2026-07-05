from __future__ import annotations

from pathlib import Path


def srt_to_ass(srt_path: Path, ass_path: Path, font_name: str = "Noto Sans CJK SC") -> None:
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    index = 0
    lines = srt_path.read_text(encoding="utf-8").splitlines()
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        index += 1
        if index >= len(lines):
            break
        timing = lines[index].strip()
        index += 1
        text_lines = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        if " --> " in timing and text_lines:
            start, end = timing.split(" --> ", 1)
            events.append((srt_time_to_ass(start), srt_time_to_ass(end), "\\N".join(text_lines)))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},58,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,4,0,2,80,80,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n" for start, end, text in events)
    ass_path.write_text(header + body, encoding="utf-8")


def srt_time_to_ass(value: str) -> str:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    second_value = float(seconds)
    return f"{int(hours)}:{int(minutes):02d}:{second_value:05.2f}"
