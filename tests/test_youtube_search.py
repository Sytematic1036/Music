"""Tests for YouTube search module."""

import pytest
from src.youtube_search import (
    parse_duration,
    parse_view_count,
    VideoResult,
    search_relaxation_music,
)


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_minutes_seconds(self):
        assert parse_duration("3:45") == 225

    def test_hours_minutes_seconds(self):
        assert parse_duration("1:23:45") == 5025

    def test_seconds_only(self):
        assert parse_duration("45") == 45

    def test_empty_string(self):
        assert parse_duration("") == 0

    def test_invalid_format(self):
        assert parse_duration("invalid") == 0


class TestParseViewCount:
    """Tests for parse_view_count function."""

    def test_simple_number(self):
        assert parse_view_count("1234567") == 1234567

    def test_with_commas(self):
        assert parse_view_count("1,234,567 views") == 1234567

    def test_k_suffix(self):
        assert parse_view_count("500K views") == 500000

    def test_m_suffix(self):
        assert parse_view_count("1.2M views") == 1200000

    def test_empty_string(self):
        assert parse_view_count("") == 0


class TestVideoResult:
    """Tests for VideoResult dataclass."""

    def test_creation(self):
        video = VideoResult(
            video_id="abc123",
            title="Test Video",
            channel="Test Channel",
            duration_seconds=300,
            view_count=1000000,
            url="https://youtube.com/watch?v=abc123"
        )
        assert video.video_id == "abc123"
        assert video.title == "Test Video"
        assert video.duration_seconds == 300
        assert video.view_count == 1000000


class TestSearchRelaxationMusic:
    """Tests for search_relaxation_music function."""

    def test_returns_list(self):
        """Test that search returns a list (may be empty without network)."""
        try:
            results = search_relaxation_music(limit=1)
            assert isinstance(results, list)
            # If we get results, verify structure
            if results:
                assert isinstance(results[0], VideoResult)
                assert results[0].video_id
                assert results[0].title
        except ImportError:
            pytest.skip("youtube-search-python not installed")
        except Exception as e:
            # Network issues are acceptable in tests
            if "network" in str(e).lower() or "connection" in str(e).lower():
                pytest.skip(f"Network unavailable: {e}")
            raise


class TestSearchWithMock:
    """Tests using mocked responses."""

    def test_search_parses_results(self, mocker):
        """Test that search correctly parses mock results."""
        # Skip if youtube-search-python not installed
        try:
            import youtubesearchpython
        except ImportError:
            pytest.skip("youtube-search-python not installed")

        mock_result = {
            "result": [
                {
                    "id": "test123",
                    "title": "Relaxing Piano Music",
                    "channel": {"name": "Calm Music"},
                    "duration": "5:30",
                    "viewCount": {"text": "1,000,000 views"},
                    "link": "https://youtube.com/watch?v=test123",
                    "thumbnails": [{"url": "https://example.com/thumb.jpg"}]
                }
            ]
        }

        # Mock the VideosSearch class from the youtubesearchpython package
        mock_search_class = mocker.patch("youtubesearchpython.VideosSearch")
        mock_instance = mock_search_class.return_value
        mock_instance.result.return_value = mock_result

        # Import and call after mocking
        from src.youtube_search import search_relaxation_music as search_fn
        results = search_fn(limit=1, min_duration_minutes=1, max_duration_minutes=60)

        assert len(results) == 1
        assert results[0].video_id == "test123"
        assert results[0].title == "Relaxing Piano Music"
        assert results[0].duration_seconds == 330  # 5:30
        assert results[0].view_count == 1000000
