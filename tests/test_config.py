from ai_roughcut.config import get_profile


def test_default_profile_is_available_for_readme_examples():
    profile = get_profile("default")

    assert profile.name == "default"


def test_default_decision_thresholds_match_documentary_readme_policy():
    profile = get_profile("default")

    assert profile.decisions.auto_confidence == 0.85
    assert profile.decisions.review_confidence == 0.70
