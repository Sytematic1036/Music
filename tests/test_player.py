"""Tests for player module."""

import pytest
from pathlib import Path
import tempfile

from src.player import (
    PlaybackMethod,
    PlaybackResult,
    create_browser_player,
    get_player_info,
    check_pygame,
    BROWSER_PLAYER_HTML,
)


class TestPlaybackMethod:
    """Tests for PlaybackMethod enum."""

    def test_all_methods_exist(self):
        assert PlaybackMethod.BROWSER is not None
        assert PlaybackMethod.PYTHON is not None
        assert PlaybackMethod.EXPORT is not None

    def test_method_values(self):
        assert PlaybackMethod.BROWSER.value == "browser"
        assert PlaybackMethod.PYTHON.value == "python"
        assert PlaybackMethod.EXPORT.value == "export"


class TestPlaybackResult:
    """Tests for PlaybackResult dataclass."""

    def test_success_result(self):
        result = PlaybackResult(
            success=True,
            method=PlaybackMethod.BROWSER,
            message="Playing",
            file_path="/path/to/file.mid"
        )
        assert result.success is True
        assert result.method == PlaybackMethod.BROWSER
        assert result.file_path is not None

    def test_failure_result(self):
        result = PlaybackResult(
            success=False,
            method=PlaybackMethod.PYTHON,
            message="pygame not installed"
        )
        assert result.success is False
        assert result.file_path is None


class TestBrowserPlayer:
    """Tests for browser player generation."""

    def test_create_browser_player(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            player_path = create_browser_player(tmpdir)

            assert Path(player_path).exists()
            assert Path(player_path).name == "player.html"

    def test_browser_player_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            player_path = create_browser_player(tmpdir)

            with open(player_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for key elements
            assert "<!DOCTYPE html>" in content
            assert "Music Pipeline Player" in content
            assert "Tone.js" in content or "tone" in content.lower()

    def test_browser_player_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            player_path = create_browser_player(subdir)

            assert Path(player_path).exists()
            assert subdir.is_dir()


class TestBrowserPlayerHTML:
    """Tests for browser player HTML template."""

    def test_html_is_valid(self):
        assert "<!DOCTYPE html>" in BROWSER_PLAYER_HTML
        assert "<html" in BROWSER_PLAYER_HTML
        assert "</html>" in BROWSER_PLAYER_HTML

    def test_html_has_stages(self):
        assert "stage-melody" in BROWSER_PLAYER_HTML
        assert "stage-arrangement" in BROWSER_PLAYER_HTML
        assert "stage-production" in BROWSER_PLAYER_HTML

    def test_html_has_controls(self):
        assert "play-btn" in BROWSER_PLAYER_HTML
        assert "stop-btn" in BROWSER_PLAYER_HTML
        assert "volume" in BROWSER_PLAYER_HTML

    def test_html_has_file_handling(self):
        assert "drop-zone" in BROWSER_PLAYER_HTML
        assert "file-input" in BROWSER_PLAYER_HTML

    def test_html_has_audio_libraries(self):
        assert "Tone" in BROWSER_PLAYER_HTML
        assert "Midi" in BROWSER_PLAYER_HTML


class TestPlayerInfo:
    """Tests for player info function."""

    def test_get_player_info(self):
        info = get_player_info()

        assert "pygame_available" in info
        assert "fluidsynth_available" in info
        assert "ffmpeg_available" in info
        assert "browser_available" in info
        assert "recommended_method" in info

        assert isinstance(info["pygame_available"], bool)
        assert isinstance(info["browser_available"], bool)
        assert info["browser_available"] is True  # Always available

    def test_recommended_method(self):
        info = get_player_info()

        assert info["recommended_method"] in ["browser", "python"]


class TestCheckPygame:
    """Tests for pygame check."""

    def test_check_pygame_returns_bool(self):
        result = check_pygame()
        assert isinstance(result, bool)


# Integration tests with actual files
class TestPlayerIntegration:
    """Integration tests for player."""

    def test_create_and_read_player(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create player
            player_path = create_browser_player(tmpdir)

            # Read it back
            with open(player_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Should be valid HTML
            assert len(content) > 1000
            assert content.startswith("<!DOCTYPE html>")

    def test_player_works_with_midi_files(self):
        from src.melody import generate_melody, melody_to_midi, MelodyParams

        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate MIDI file
            params = MelodyParams(duration_seconds=5)
            melody = generate_melody(params, seed=42)
            midi_path = Path(tmpdir) / "test.mid"
            melody_to_midi(melody, midi_path)

            # Create player in same dir
            player_path = create_browser_player(tmpdir)

            # Both should exist
            assert Path(midi_path).exists()
            assert Path(player_path).exists()

            # Player should be in same directory
            assert Path(player_path).parent == midi_path.parent
