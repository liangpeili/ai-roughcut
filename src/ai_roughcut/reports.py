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
    if rows:
        table_body = "".join(rows)
    else:
        table_body = '<tr><td colspan="6">没有需要人工复查的片段；仍建议完整播放 rough_cut.mp4，确认节奏和语义自然。</td></tr>'
    average_confidence = _average_confidence(review_items)
    confidence_text = "无" if average_confidence is None else f"{average_confidence:.2f}"
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>AI Roughcut Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #1f2933; }}
    .summary {{ display: flex; gap: 16px; margin: 20px 0; flex-wrap: wrap; }}
    .metric {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; min-width: 140px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .checklist {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 18px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
  </style>
</head>
<body>
  <h1>人工复查清单</h1>
  <section>
    <h2>复查摘要</h2>
    <div class="summary">
      <div class="metric">待复查片段<strong>{len(review_items)}</strong></div>
      <div class="metric">平均置信度<strong>{confidence_text}</strong></div>
    </div>
  </section>
  <section class="checklist">
    <h2>审核重点</h2>
    <ul>
      <li>句首或句尾有没有被吃掉。</li>
      <li>长空白压缩后是否仍保留人物思考和情绪。</li>
      <li>被访者表达是否完整，语义有没有被误删。</li>
      <li>低置信度、AI 返回异常或敏感内容是否需要手动调整。</li>
      <li>导入剪映后，字幕、声音和画面是否对齐。</li>
    </ul>
  </section>
  <table>
    <thead><tr><th>开始</th><th>结束</th><th>置信度</th><th>说话人</th><th>文本</th><th>原因</th></tr></thead>
    <tbody>{table_body}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def _average_confidence(review_items: list[ReviewItem]) -> float | None:
    values = [item.confidence for item in review_items if item.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)
