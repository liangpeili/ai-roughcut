from ai_roughcut.config import get_profile


def test_default_profile_is_available_for_readme_examples():
    profile = get_profile("default")

    assert profile.name == "default"


def test_default_decision_thresholds_use_practical_ai_policy():
    profile = get_profile("default")

    assert profile.decisions.auto_confidence == 0.75
    assert profile.decisions.review_confidence == 0.60
