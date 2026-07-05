from __future__ import annotations

import csv
import html
from pathlib import Path

from .models import ReviewItem


def write_review_csv(path: Path, review_items: list[ReviewItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["start", "end", "confidence", "speaker", "text", "reason"])
        writer.writeheader()
        for item in review_items:
            writer.writerow(item.to_dict())


def write_review_html(path: Path, review_items: list[ReviewItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in review_items:
        rows.append(
            "<tr>"
            f"<td>{item.start:.2f}</td>"
            f"<td>{item.end:.2f}</td>"
            f"<td>{'' if item.confidence is None else f'{item.confidence:.2f}'}</td>"
            f"<td>{html.escape(item.speaker or '')}</td>"
            f"<td>{html.escape(item.text)}</td>"
            f"<td>{html.escape(item.reason)}</td>"
            "</tr>"
        )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>AI Roughcut Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
  </style>
</head>
<body>
  <h1>人工复查清单</h1>
  <table>
    <thead><tr><th>开始</th><th>结束</th><th>置信度</th><th>说话人</th><th>文本</th><th>原因</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
