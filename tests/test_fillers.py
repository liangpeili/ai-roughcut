from ai_roughcut.config import get_profile
from ai_roughcut.fillers import find_filler_candidates, normalize_word


def test_normalize_word_strips_chinese_and_ascii_punctuation():
    assert normalize_word("，嗯。") == "嗯"
    assert normalize_word("啊?") == "啊"


def test_find_filler_candidates_reads_whisperx_words():
    transcript = {
        "segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "我觉得 嗯 主要是",
                "words": [
                    {"word": "我觉得", "start": 12.4, "end": 12.82},
                    {"word": "嗯", "start": 12.9, "end": 13.15},
                    {"word": "主要是", "start": 13.3, "end": 13.76},
                ],
            }
        ]
    }

    candidates = find_filler_candidates(transcript, get_profile("lianglaoshi").filler_words)

    assert len(candidates) == 1
    assert candidates[0].text == "嗯"
    assert candidates[0].speaker == "SPEAKER_00"
