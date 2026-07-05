from ai_roughcut.config import get_profile


def test_default_profile_is_available_for_readme_examples():
    profile = get_profile("default")

    assert profile.name == "default"
