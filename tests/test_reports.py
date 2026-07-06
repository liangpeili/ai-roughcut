from ai_roughcut.models import ReviewItem
from ai_roughcut.reports import write_review_html


def test_write_review_html_includes_summary_and_audit_checklist(tmp_path):
    path = tmp_path / "review_report.html"
    review_items = [
        ReviewItem(start=1.0, end=2.5, reason="置信度低", confidence=0.55, text="嗯", speaker="SPEAKER_00"),
        ReviewItem(start=8.0, end=9.0, reason="AI 未返回该候选，转人工复查", confidence=0.0),
    ]

    write_review_html(path, review_items)

    document = path.read_text(encoding="utf-8")
    assert "复查摘要" in document
    assert "待复查片段" in document
    assert "2" in document
    assert "审核重点" in document
    assert "句首或句尾有没有被吃掉" in document
    assert "置信度低" in document
    assert "AI 未返回该候选" in document


def test_write_review_html_shows_empty_state_when_no_review_items(tmp_path):
    path = tmp_path / "review_report.html"

    write_review_html(path, [])

    document = path.read_text(encoding="utf-8")
    assert "没有需要人工复查的片段" in document
    assert "仍建议完整播放 rough_cut.mp4" in document
