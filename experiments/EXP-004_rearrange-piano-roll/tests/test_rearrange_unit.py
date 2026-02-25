"""
Unit tests for player_rearrange module (no browser needed).

Tests the Python functions without requiring Playwright.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestPlayerRearrangeModule:
    """Unit tests for player_rearrange.py"""

    def test_import(self):
        """Test that module can be imported."""
        from player_rearrange import (
            PlaybackMethod,
            PlaybackResult,
            create_browser_player_with_rearrange,
            BROWSER_PLAYER_WITH_REARRANGE_HTML
        )

        assert PlaybackMethod.BROWSER.value == "browser"
        assert BROWSER_PLAYER_WITH_REARRANGE_HTML is not None
        assert len(BROWSER_PLAYER_WITH_REARRANGE_HTML) > 1000

    def test_html_contains_rearrange_tab(self):
        """Test that HTML includes the Rearrange tab."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check tab exists
        assert 'data-tab="rearrange"' in html
        assert 'id="tab-rearrange"' in html

        # Check piano roll canvas
        assert 'id="piano-roll-canvas"' in html

        # Check controls
        assert 'id="zoom-x"' in html
        assert 'id="zoom-y"' in html
        assert 'id="snap-select"' in html
        assert 'id="export-btn"' in html

    def test_html_contains_player_tab(self):
        """Test that original Player tab is preserved."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check Player tab elements
        assert 'data-tab="player"' in html
        assert 'id="tab-player"' in html
        assert 'id="play-btn"' in html
        assert 'id="stop-btn"' in html

    def test_html_contains_piano_roll_logic(self):
        """Test that piano roll JavaScript is included."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check piano roll object
        assert 'const pianoRoll' in html
        assert 'pianoRoll.init()' in html

        # Check key methods
        assert 'getNoteAt' in html
        assert 'onMouseDown' in html
        assert 'onMouseMove' in html
        assert 'deleteNote' in html
        assert 'exportMidi' in html

    def test_html_contains_tone_js(self):
        """Test that Tone.js is included for MIDI playback."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        assert 'cdn.jsdelivr.net/npm/tone' in html
        assert 'cdn.jsdelivr.net/npm/@tonejs/midi' in html

    def test_create_browser_player_with_rearrange(self):
        """Test that HTML file is created correctly."""
        from player_rearrange import create_browser_player_with_rearrange

        with tempfile.TemporaryDirectory() as tmpdir:
            player_path = create_browser_player_with_rearrange(tmpdir)

            assert os.path.exists(player_path)
            assert player_path.endswith('player.html')

            with open(player_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'Rearrange' in content
            assert 'piano-roll-canvas' in content

    def test_playback_result_dataclass(self):
        """Test PlaybackResult dataclass."""
        from player_rearrange import PlaybackResult, PlaybackMethod

        result = PlaybackResult(
            success=True,
            method=PlaybackMethod.BROWSER,
            message="Test message",
            file_path="/path/to/file"
        )

        assert result.success is True
        assert result.method == PlaybackMethod.BROWSER
        assert result.message == "Test message"
        assert result.file_path == "/path/to/file"

    def test_playback_method_enum(self):
        """Test PlaybackMethod enum values."""
        from player_rearrange import PlaybackMethod

        assert PlaybackMethod.BROWSER.value == "browser"
        assert PlaybackMethod.PYTHON.value == "python"
        assert PlaybackMethod.EXPORT.value == "export"


class TestHTMLStructure:
    """Test the HTML structure in detail."""

    def test_css_styles_present(self):
        """Test that CSS styles are included."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check style tag
        assert '<style>' in html
        assert '</style>' in html

        # Check key CSS classes
        assert '.tabs' in html
        assert '.tab.active' in html
        assert '.piano-roll-container' in html
        assert '.piano-keys' in html
        assert '.track-list' in html

    def test_drag_drop_zone(self):
        """Test that drag-drop zone is configured."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check drop zone for Rearrange tab
        assert 'id="rearrange-drop-zone"' in html
        assert 'accept=".mid,.midi"' in html

    def test_click_to_browse(self):
        """Test that click-to-browse is available."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check click handler in JavaScript
        assert "dropZone.addEventListener('click'" in html
        assert "fileInput.click()" in html

        # Check visual hints
        assert 'click to browse' in html
        assert 'cursor: pointer' in html

    def test_canvas_dimensions(self):
        """Test canvas has correct dimensions."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check canvas attributes
        assert 'width="1000"' in html
        assert 'height="600"' in html

    def test_help_text_present(self):
        """Test that help text is included."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        assert 'Drag note horizontally' in html
        assert 'change time' in html
        assert 'change pitch' in html
        assert 'Delete' in html

    def test_clear_button(self):
        """Test that clear button exists and has handler."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Check button exists
        assert 'id="clear-btn"' in html
        assert '>Clear<' in html

        # Check event handler
        assert "clear-btn" in html
        assert "addEventListener('click'" in html

        # Check clear method exists
        assert 'clear()' in html
        assert 'this.notes = []' in html


class TestJavaScriptLogic:
    """Test JavaScript functionality structure."""

    def test_tab_switching_logic(self):
        """Test tab switching code is present."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        assert "querySelectorAll('.tab')" in html
        assert 'classList.add' in html
        assert 'classList.remove' in html

    def test_piano_roll_initialization(self):
        """Test piano roll initialization code."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        assert 'init()' in html
        assert 'setupPianoKeys()' in html
        assert 'setupEventListeners()' in html
        assert 'render()' in html

    def test_note_editing_methods(self):
        """Test note editing methods are present."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        # Selection
        assert 'selectedNote' in html
        assert 'getNoteAt' in html

        # Dragging
        assert 'isDragging' in html
        assert 'dragStartX' in html
        assert 'dragStartY' in html

        # History
        assert 'saveToHistory' in html
        assert 'undo' in html

    def test_midi_export(self):
        """Test MIDI export functionality is present."""
        from player_rearrange import BROWSER_PLAYER_WITH_REARRANGE_HTML

        html = BROWSER_PLAYER_WITH_REARRANGE_HTML

        assert 'exportMidi' in html
        assert 'new Midi()' in html
        assert 'toArray()' in html
        assert 'download' in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
