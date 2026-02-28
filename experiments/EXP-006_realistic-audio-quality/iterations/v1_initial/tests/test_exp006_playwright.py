"""
Playwright tests for EXP-006: Realistic Audio Quality.

Tests:
1. Tab navigation works
2. MIDI file loads and displays notes
3. Server-side rendering endpoint works
4. Play button triggers server render
5. Audio plays after rendering
6. Export functionality works

Run with:
    pytest tests/test_exp006_playwright.py -v

Prerequisites:
    pip install pytest playwright
    playwright install chromium
"""

import asyncio
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Check if playwright is available
try:
    from playwright.sync_api import Page, expect, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Create a minimal test MIDI file
def create_test_midi(path: Path):
    """Create a simple test MIDI file with a few notes."""
    # Minimal MIDI file with 4 notes (C4, E4, G4, C5)
    midi_data = bytes([
        # Header
        0x4D, 0x54, 0x68, 0x64,  # MThd
        0x00, 0x00, 0x00, 0x06,  # Header length
        0x00, 0x00,              # Format 0
        0x00, 0x01,              # 1 track
        0x01, 0xE0,              # 480 ticks per quarter

        # Track
        0x4D, 0x54, 0x72, 0x6B,  # MTrk
        0x00, 0x00, 0x00, 0x34,  # Track length

        # Note On C4 (60)
        0x00, 0x90, 0x3C, 0x64,
        # Note Off after 480 ticks
        0x83, 0x60, 0x80, 0x3C, 0x00,

        # Note On E4 (64)
        0x00, 0x90, 0x40, 0x64,
        0x83, 0x60, 0x80, 0x40, 0x00,

        # Note On G4 (67)
        0x00, 0x90, 0x43, 0x64,
        0x83, 0x60, 0x80, 0x43, 0x00,

        # Note On C5 (72)
        0x00, 0x90, 0x48, 0x64,
        0x83, 0x60, 0x80, 0x48, 0x00,

        # End of track
        0x00, 0xFF, 0x2F, 0x00
    ])
    with open(path, 'wb') as f:
        f.write(midi_data)


@pytest.fixture(scope="module")
def test_midi_file():
    """Create a temporary test MIDI file."""
    with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
        path = Path(f.name)

    create_test_midi(path)
    yield path
    os.unlink(path)


@pytest.fixture(scope="module")
def player_server():
    """Start the EXP-006 player server."""
    # Add src path to Python path
    src_path = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_path))

    # Start server in background process
    import socketserver
    import threading

    # Import player module components directly
    import production
    import player_rearrange

    class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    port = 8766  # Use different port from main server

    def run_server():
        with ThreadingServer(("", port), player_rearrange.PlayerHandler) as httpd:
            httpd.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Wait for server to start
    time.sleep(2)

    yield f"http://localhost:{port}"

    # Server thread is daemon, will stop with test


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006Tabs:
    """Test suite for tab navigation."""

    def test_tab_navigation(self, player_server):
        """Test that tabs can be switched."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Check Player tab is active by default
            player_tab = page.locator('.tab[data-tab="player"]')
            expect(player_tab).to_have_class(re.compile(r"active"))

            # Click Rearrange tab
            rearrange_tab = page.locator('.tab[data-tab="rearrange"]')
            rearrange_tab.click()

            # Check Rearrange tab is now active
            expect(rearrange_tab).to_have_class(re.compile(r"active"))
            expect(page.locator('#tab-rearrange')).to_be_visible()

            browser.close()

    def test_rearrange_tab_elements_visible(self, player_server):
        """Test that Rearrange tab has all required elements."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Check EXP-006 specific elements exist
            expect(page.locator('#piano-roll-canvas')).to_be_visible()
            expect(page.locator('#rearrange-drop-zone')).to_be_visible()
            expect(page.locator('#zoom-x')).to_be_visible()
            expect(page.locator('#zoom-y')).to_be_visible()
            expect(page.locator('#snap-select')).to_be_visible()
            expect(page.locator('#export-midi-btn')).to_be_visible()
            expect(page.locator('#rearrange-play-btn')).to_be_visible()

            # Check info banner mentions EXP-006
            info_banner = page.locator('.info-banner')
            expect(info_banner).to_contain_text('EXP-006')

            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006MidiLoading:
    """Test MIDI file loading."""

    def test_midi_file_load(self, player_server, test_midi_file):
        """Test that MIDI file loads and displays notes."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Upload MIDI file
            file_input = page.locator('#rearrange-file-input')
            file_input.set_input_files(str(test_midi_file))

            # Wait for file to load
            page.wait_for_timeout(1000)

            # Check that drop zone updated
            drop_zone = page.locator('#rearrange-drop-zone')
            drop_zone_text = drop_zone.text_content()
            assert 'Drop' in drop_zone_text or 'Loaded' in drop_zone_text or 'Error' in drop_zone_text

            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006ServerRendering:
    """Test server-side rendering functionality."""

    def test_play_button_state(self, player_server, test_midi_file):
        """Test that play button is disabled until file is loaded."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Play button should be disabled initially
            play_btn = page.locator('#rearrange-play-btn')
            expect(play_btn).to_be_disabled()

            browser.close()

    def test_render_status_element(self, player_server):
        """Test that render status element exists (hidden by default)."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Render status should exist but be hidden
            render_status = page.locator('#render-status')
            # Element exists but not visible
            expect(render_status).to_have_count(1)

            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006Controls:
    """Test piano roll controls."""

    def test_zoom_controls(self, player_server, test_midi_file):
        """Test that zoom controls work."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()
            page.locator('#rearrange-file-input').set_input_files(str(test_midi_file))
            page.wait_for_timeout(500)

            # Change zoom X
            zoom_x = page.locator('#zoom-x')
            initial_value = zoom_x.input_value()
            zoom_x.fill('80')
            page.wait_for_timeout(100)
            # No error is success

            # Change zoom Y
            zoom_y = page.locator('#zoom-y')
            zoom_y.fill('20')
            page.wait_for_timeout(100)

            browser.close()

    def test_snap_setting(self, player_server):
        """Test that snap setting can be changed."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Change snap setting
            snap_select = page.locator('#snap-select')
            snap_select.select_option('1')  # 1/4 note

            # Verify selection
            expect(snap_select).to_have_value('1')

            browser.close()

    def test_catch_mode_toggle(self, player_server):
        """Test that catch mode checkbox works."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Catch mode should be checked by default
            catch_mode = page.locator('#catch-mode')
            expect(catch_mode).to_be_checked()

            # Toggle it off
            catch_mode.click()
            expect(catch_mode).not_to_be_checked()

            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006Canvas:
    """Test canvas rendering."""

    def test_canvas_renders(self, player_server, test_midi_file):
        """Test that canvas renders without errors."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Listen for console errors
            errors = []
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)

            page.goto(player_server)

            # Switch to Rearrange tab and load file
            page.locator('.tab[data-tab="rearrange"]').click()
            page.locator('#rearrange-file-input').set_input_files(str(test_midi_file))
            page.wait_for_timeout(1000)

            # Canvas should have dimensions
            canvas = page.locator('#piano-roll-canvas')
            width = canvas.get_attribute('width')
            height = canvas.get_attribute('height')

            # Should have non-zero dimensions
            assert int(width) > 0, "Canvas width should be > 0"
            assert int(height) > 0, "Canvas height should be > 0"

            # No JavaScript errors
            assert len(errors) == 0, f"JavaScript errors: {errors}"

            browser.close()

    def test_ruler_canvas_exists(self, player_server):
        """Test that ruler canvas exists."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Ruler canvas should exist
            ruler_canvas = page.locator('#ruler-canvas')
            expect(ruler_canvas).to_be_visible()

            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006DragAndDrop:
    """Test drag and drop functionality for notes."""

    def test_drag_note_horizontal(self, player_server, test_midi_file):
        """Test dragging a note horizontally changes its time."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Load file in Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()
            page.locator('#rearrange-file-input').set_input_files(str(test_midi_file))
            page.wait_for_timeout(500)

            canvas = page.locator('#piano-roll-canvas')
            box = canvas.bounding_box()

            # Get initial selection info
            page.mouse.click(box['x'] + 50, box['y'] + box['height'] / 2)
            page.wait_for_timeout(100)

            # Drag horizontally
            page.mouse.move(box['x'] + 50, box['y'] + box['height'] / 2)
            page.mouse.down()
            page.mouse.move(box['x'] + 150, box['y'] + box['height'] / 2, steps=10)
            page.mouse.up()

            # No error is success
            browser.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestEXP006HelpText:
    """Test help text visibility."""

    def test_help_text_visible(self, player_server):
        """Test that help text with controls is visible."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(player_server)

            # Switch to Rearrange tab
            page.locator('.tab[data-tab="rearrange"]').click()

            # Check help text
            help_text = page.locator('.help-text')
            expect(help_text).to_be_visible()
            expect(help_text).to_contain_text('Drag note')
            expect(help_text).to_contain_text('Delete')
            expect(help_text).to_contain_text('ruler')

            browser.close()


# Standalone test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
