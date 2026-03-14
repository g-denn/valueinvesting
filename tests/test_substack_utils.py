from app.services.substack import (
    normalize_source_url,
    source_name_from_url,
    source_to_rss_url,
)


def test_substack_url_normalization_and_rss():
    assert normalize_source_url("mscliffnotes.substack.com") == "https://mscliffnotes.substack.com/"
    assert source_to_rss_url("https://mscliffnotes.substack.com/") == "https://mscliffnotes.substack.com/feed"


def test_profile_handle_conversion():
    assert source_to_rss_url("https://substack.com/@fairyiiliew") == "https://fairyiiliew.substack.com/feed"
    assert source_name_from_url("https://substack.com/@valueinvietnam") == "valueinvietnam"
