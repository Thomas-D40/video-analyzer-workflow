"""
Unit tests for app/utils/youtube.py

Tests extract_video_id for all supported URL formats.
"""
from app.utils.youtube import extract_video_id

VALID_VIDEO_ID = "dQw4w9WgXcQ"


def test_extract_video_id_standard_url():
    url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"
    assert extract_video_id(url) == VALID_VIDEO_ID


def test_extract_video_id_standard_url_no_www():
    url = f"https://youtube.com/watch?v={VALID_VIDEO_ID}"
    assert extract_video_id(url) == VALID_VIDEO_ID


def test_extract_video_id_short_url():
    url = f"https://youtu.be/{VALID_VIDEO_ID}"
    assert extract_video_id(url) == VALID_VIDEO_ID


def test_extract_video_id_embed_url():
    url = f"https://www.youtube.com/embed/{VALID_VIDEO_ID}"
    assert extract_video_id(url) == VALID_VIDEO_ID


def test_extract_video_id_with_extra_params():
    url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&t=42s&list=PLxxx"
    assert extract_video_id(url) == VALID_VIDEO_ID


def test_extract_video_id_invalid_url():
    assert extract_video_id("https://vimeo.com/123456789") is None


def test_extract_video_id_no_id():
    assert extract_video_id("https://www.youtube.com/watch") is None


def test_extract_video_id_empty_string():
    assert extract_video_id("") is None


def test_extract_video_id_non_url():
    assert extract_video_id("not a url at all") is None


def test_extract_video_id_short_url_wrong_length():
    # youtu.be IDs must be exactly 11 chars
    assert extract_video_id("https://youtu.be/short") is None
