"""Tests for audio downloader module."""

import pytest
from pathlib import Path
from src.downloader import (
    check_yt_dlp_installed,
    download_audio,
    DownloadResult,
)


class TestCheckYtDlpInstalled:
    """Tests for yt-dlp installation check."""

    def test_returns_boolean(self):
        """Check returns a boolean value."""
        result = check_yt_dlp_installed()
        assert isinstance(result, bool)


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_success_result(self):
        result = DownloadResult(
            success=True,
            file_path="/path/to/file.wav",
            duration_seconds=120.5
        )
        assert result.success is True
        assert result.file_path == "/path/to/file.wav"
        assert result.error is None

    def test_error_result(self):
        result = DownloadResult(
            success=False,
            error="Download failed"
        )
        assert result.success is False
        assert result.file_path is None
        assert result.error == "Download failed"


class TestDownloadAudio:
    """Tests for download_audio function."""

    def test_invalid_url_handling(self, tmp_path):
        """Test handling of invalid URLs."""
        if not check_yt_dlp_installed():
            pytest.skip("yt-dlp not installed")

        result = download_audio(
            url="https://youtube.com/watch?v=invalid_video_id_12345",
            output_dir=tmp_path,
            max_duration_seconds=60
        )

        # Should handle gracefully (either error or empty result)
        assert isinstance(result, DownloadResult)
        # Invalid URLs should fail
        # Note: This may take time to timeout

    def test_returns_download_result(self, mocker):
        """Test that download returns DownloadResult."""
        # Mock check_yt_dlp_installed to return False
        mocker.patch("src.downloader.check_yt_dlp_installed", return_value=False)

        result = download_audio(
            url="https://youtube.com/watch?v=test",
            output_dir="/tmp"
        )

        assert isinstance(result, DownloadResult)
        assert result.success is False
        assert "yt-dlp" in result.error.lower()
