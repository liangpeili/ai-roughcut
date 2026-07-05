from ai_roughcut.config import SilencePolicy
from ai_roughcut.silence import classify_silence, parse_ffmpeg_silencedetect


def test_classify_silence_ignores_short_pause():
    policy = SilencePolicy()

    assert classify_silence(1.0, 1.6, policy) is None


def test_classify_silence_marks_medium_pause_without_auto_compress():
    policy = SilencePolicy()

    candidate = classify_silence(1.0, 2.0, policy)

    assert candidate is not None
    assert candidate.suggestion == "mark"
    assert candidate.duration == 1.0


def test_classify_silence_compresses_long_pause():
    policy = SilencePolicy()

    candidate = classify_silence(10.0, 12.0, policy)

    assert candidate is not None
    assert candidate.suggestion == "compress"
    assert "0.4" in candidate.reason


def test_parse_ffmpeg_silencedetect_pairs_start_and_end():
    policy = SilencePolicy()
    stderr = """
    [silencedetect @ 0x00] silence_start: 42.1
    [silencedetect @ 0x00] silence_end: 44.8 | silence_duration: 2.7
    """

    candidates = parse_ffmpeg_silencedetect(stderr, policy)

    assert len(candidates) == 1
    assert candidates[0].start == 42.1
    assert candidates[0].end == 44.8
    assert candidates[0].suggestion == "compress"
