"""
Extended player module with Rearrange tab - Version 2.

New features in v2:
- Load MP3/WAV files and convert to MIDI for editing
- Logic-like track view with separate channels
- Playback of edited notes with Tone.js synth
- Save button to export edited MIDI back to MP3/WAV

This module provides:
1. HTTP server for file upload and conversion
2. WebSocket for real-time communication
3. Audio-to-MIDI conversion via librosa
4. MIDI-to-audio rendering via FluidSynth or Tone.js
"""

import base64
import http.server
import io
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))
from audio_to_midi import analyze_audio, notes_to_midi, audio_to_midi_json


class PlaybackMethod(Enum):
    """Available playback methods."""
    BROWSER = "browser"
    PYTHON = "python"
    EXPORT = "export"


@dataclass
class PlaybackResult:
    """Result of playback operation."""
    success: bool
    method: PlaybackMethod
    message: str = ""
    file_path: Optional[str] = None


# Check for FluidSynth availability
def check_fluidsynth() -> bool:
    """Check if FluidSynth is available."""
    try:
        # Use -V (short version flag) which works on Windows
        result = subprocess.run(
            ["fluidsynth", "-V"],
            capture_output=True,
            timeout=5
        )
        # FluidSynth may return non-zero but still output version info
        return b"FluidSynth" in result.stdout or b"FluidSynth" in result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def find_soundfont() -> Optional[str]:
    """Find a SoundFont file for FluidSynth."""
    # Common locations - prioritize the one we downloaded
    locations = [
        # Downloaded SoundFont
        "C:/soundfonts/FluidR3_GM.sf2",
        # Windows alternatives
        "C:/Program Files/FluidSynth/share/soundfonts/default.sf2",
        os.path.expanduser("~/soundfonts/FluidR3_GM.sf2"),
        # Chocolatey FluidSynth
        "C:/ProgramData/chocolatey/lib/fluidsynth/share/soundfonts/FluidR3_GM.sf2",
        # Linux/Mac
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/FluidR3_GM.sf2",
    ]

    for loc in locations:
        if os.path.exists(loc):
            print(f"Found SoundFont: {loc}")
            return loc

    print("No SoundFont found. Looked in:", locations)
    return None


def midi_to_audio(
    midi_path: str | Path,
    output_path: str | Path,
    format: str = "wav",
    soundfont: Optional[str] = None
) -> bool:
    """
    Convert MIDI to audio using FluidSynth.

    Args:
        midi_path: Path to MIDI file
        output_path: Path for output audio
        format: Output format ("wav" or "mp3")
        soundfont: Path to SoundFont file

    Returns:
        True if successful
    """
    if not check_fluidsynth():
        print("FluidSynth not available")
        return False

    if soundfont is None:
        soundfont = find_soundfont()
        if soundfont is None:
            print("No SoundFont found")
            return False

    midi_path = Path(midi_path)
    output_path = Path(output_path)

    # FluidSynth command
    wav_output = output_path if format == "wav" else output_path.with_suffix(".wav")

    cmd = [
        "fluidsynth",
        "-ni",  # No interactive mode
        "-g", "1.0",  # Gain
        "-F", str(wav_output),  # Output file
        soundfont,
        str(midi_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            print(f"FluidSynth error: {result.stderr.decode()}")
            return False

        # Convert to MP3 if needed
        if format == "mp3" and wav_output.exists():
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_output), "-b:a", "192k", str(output_path)],
                    capture_output=True,
                    timeout=60
                )
                wav_output.unlink()  # Remove temp WAV
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # ffmpeg not available, keep WAV
                output_path = wav_output

        return output_path.exists()

    except subprocess.TimeoutExpired:
        print("FluidSynth timeout")
        return False


# HTML template with audio upload and save functionality
BROWSER_PLAYER_V2_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Player - EXP-004 v2 Rearrange</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }

        /* Tab Navigation */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            background: rgba(255,255,255,0.1);
            color: #aaa;
            border: none;
            padding: 12px 24px;
            border-radius: 10px 10px 0 0;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab:hover {
            background: rgba(255,255,255,0.15);
            color: #fff;
        }
        .tab.active {
            background: rgba(233,69,96,0.3);
            color: #e94560;
            border-bottom: 2px solid #e94560;
        }

        /* Tab Content */
        .tab-content {
            display: none;
            width: 100%;
            max-width: 1400px;
        }
        .tab-content.active {
            display: block;
        }

        /* Player Panel */
        .player {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
            margin: 0 auto;
        }
        h1, h2 {
            font-size: 1.5rem;
            margin-bottom: 10px;
            color: #e94560;
        }
        .stage {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.9rem;
            color: #aaa;
        }
        .stage.active {
            background: rgba(233,69,96,0.2);
            border: 1px solid #e94560;
            color: #fff;
        }
        .stage h3 {
            color: #e94560;
            margin-bottom: 5px;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 30px 0;
            flex-wrap: wrap;
        }
        button {
            background: #e94560;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 50px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            background: #ff6b6b;
            transform: scale(1.05);
        }
        button:disabled {
            background: #555;
            cursor: not-allowed;
            transform: none;
        }
        button.secondary {
            background: #4ade80;
        }
        button.secondary:hover {
            background: #22c55e;
        }
        .progress {
            background: rgba(255,255,255,0.1);
            height: 8px;
            border-radius: 4px;
            margin: 20px 0;
            overflow: hidden;
        }
        .progress-bar {
            background: #e94560;
            height: 100%;
            width: 0%;
            transition: width 0.1s;
        }
        .time {
            font-size: 0.9rem;
            color: #aaa;
        }
        .file-info {
            margin-top: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            font-size: 0.85rem;
            color: #888;
        }
        #drop-zone {
            border: 2px dashed #555;
            border-radius: 10px;
            padding: 40px;
            margin: 20px 0;
            transition: all 0.3s;
            cursor: pointer;
        }
        #drop-zone:hover {
            border-color: #888;
        }
        #drop-zone.drag-over {
            border-color: #e94560;
            background: rgba(233,69,96,0.1);
        }
        .volume-control {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        input[type="range"] {
            width: 150px;
        }

        /* ============================================ */
        /* REARRANGE TAB - Logic-like Piano Roll       */
        /* ============================================ */
        .rearrange-panel {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }

        .rearrange-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }

        .toolbar-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .toolbar-label {
            color: #aaa;
            font-size: 0.85rem;
        }

        #rearrange-drop-zone {
            border: 2px dashed #555;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin-bottom: 15px;
            transition: all 0.3s;
            cursor: pointer;
        }
        #rearrange-drop-zone:hover {
            border-color: #888;
            background: rgba(255,255,255,0.02);
        }
        #rearrange-drop-zone.drag-over {
            border-color: #e94560;
            background: rgba(233,69,96,0.1);
        }
        #rearrange-drop-zone.has-file {
            border-color: #4ade80;
            background: rgba(74,222,128,0.1);
        }
        #rearrange-drop-zone.converting {
            border-color: #f59e0b;
            background: rgba(245,158,11,0.1);
        }

        /* Logic-like track headers */
        .track-headers {
            display: flex;
            flex-direction: column;
            width: 150px;
            margin-right: 10px;
        }

        .track-header {
            height: 80px;
            background: rgba(255,255,255,0.05);
            border-bottom: 1px solid #333;
            padding: 10px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .track-header .track-name {
            font-weight: bold;
            color: #fff;
            margin-bottom: 5px;
        }

        .track-header .track-info {
            font-size: 0.75rem;
            color: #888;
        }

        .track-header .track-color-bar {
            width: 4px;
            height: 100%;
            position: absolute;
            left: 0;
            top: 0;
        }

        /* Piano roll container with tracks */
        .piano-roll-wrapper {
            display: flex;
        }

        .piano-roll-container {
            position: relative;
            background: #111;
            border-radius: 10px;
            overflow: hidden;
            flex: 1;
        }

        .piano-keys {
            position: absolute;
            left: 0;
            top: 0;
            width: 50px;
            height: 100%;
            background: #222;
            border-right: 1px solid #333;
            z-index: 10;
        }

        .piano-key {
            height: 15px;
            border-bottom: 1px solid #333;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 5px;
            font-size: 9px;
            color: #666;
        }
        .piano-key.black {
            background: #1a1a1a;
        }
        .piano-key.white {
            background: #2a2a2a;
        }

        #piano-roll-canvas {
            display: block;
            margin-left: 50px;
            cursor: default;
        }

        /* Track list (Logic-like) */
        .track-list {
            display: flex;
            flex-direction: column;
            gap: 5px;
            margin-top: 15px;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
        }

        .track-item {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.05);
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .track-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .track-item.active {
            background: rgba(233,69,96,0.2);
            border-left: 3px solid #e94560;
        }
        .track-item.muted {
            opacity: 0.5;
        }

        .track-item .track-color {
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }

        .track-item .track-name {
            flex: 1;
            font-weight: 500;
        }

        .track-item .track-notes {
            color: #888;
            font-size: 0.85rem;
        }

        .track-item .track-mute {
            background: none;
            border: 1px solid #555;
            color: #888;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.75rem;
            cursor: pointer;
        }
        .track-item .track-mute:hover {
            border-color: #888;
            color: #fff;
        }
        .track-item .track-mute.active {
            background: #e94560;
            border-color: #e94560;
            color: #fff;
        }

        .track-item .track-solo {
            background: none;
            border: 1px solid #555;
            color: #888;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.75rem;
            cursor: pointer;
        }
        .track-item .track-solo:hover {
            border-color: #f59e0b;
            color: #f59e0b;
        }
        .track-item .track-solo.active {
            background: #f59e0b;
            border-color: #f59e0b;
            color: #000;
        }

        /* Status bar */
        .status-bar {
            margin-top: 15px;
            padding: 10px 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 5px;
            font-size: 0.85rem;
            color: #888;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
        }

        /* Help text */
        .help-text {
            margin-top: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            font-size: 0.8rem;
            color: #666;
        }
        .help-text kbd {
            background: #333;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }

        /* Save dialog */
        .save-dialog {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .save-dialog.active {
            display: flex;
        }
        .save-dialog-content {
            background: #1a1a2e;
            padding: 30px;
            border-radius: 15px;
            max-width: 400px;
            width: 90%;
        }
        .save-dialog h3 {
            color: #e94560;
            margin-bottom: 20px;
        }
        .save-option {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 10px 0;
        }
        .save-option label {
            color: #aaa;
        }
        .save-dialog-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        /* Loading spinner */
        .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 2px solid #555;
            border-top-color: #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        .spinner.active {
            display: inline-block;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Playback controls in Rearrange */
        .playback-controls {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
        }

        .playback-time {
            font-family: monospace;
            color: #4ade80;
            font-size: 1.2rem;
        }

        .playback-slider {
            flex: 1;
            height: 8px;
            -webkit-appearance: none;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            cursor: pointer;
        }
        .playback-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            background: #e94560;
            border-radius: 50%;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <!-- Tab Navigation -->
    <div class="tabs">
        <button class="tab active" data-tab="player">Player</button>
        <button class="tab" data-tab="rearrange">Rearrange</button>
    </div>

    <!-- Player Tab -->
    <div class="tab-content active" id="tab-player">
        <div class="player">
            <h1>Music Pipeline Player</h1>

            <div id="stages">
                <div class="stage" id="stage-melody">
                    <h3>1. Melody</h3>
                    <p>Base melodic line</p>
                </div>
                <div class="stage" id="stage-arrangement">
                    <h3>2. Arrangement</h3>
                    <p>Multi-track instruments</p>
                </div>
                <div class="stage" id="stage-production">
                    <h3>3. Production</h3>
                    <p>Mixed & mastered audio</p>
                </div>
            </div>

            <div id="drop-zone">
                <p>Drop MIDI/WAV/MP3 file here</p>
                <p style="font-size: 0.8rem; color: #666; margin-top: 10px">or click to select</p>
                <input type="file" id="file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            </div>

            <div class="progress">
                <div class="progress-bar" id="progress"></div>
            </div>

            <div class="time">
                <span id="current-time">0:00</span> / <span id="total-time">0:00</span>
            </div>

            <div class="controls">
                <button id="play-btn" disabled>Play</button>
                <button id="stop-btn" disabled>Stop</button>
                <button id="player-clear-btn" disabled>Clear</button>
            </div>

            <div class="volume-control">
                <span>Volume:</span>
                <input type="range" id="volume" min="0" max="100" value="80">
            </div>

            <div class="file-info" id="file-info">
                No file loaded
            </div>
        </div>
    </div>

    <!-- Rearrange Tab -->
    <div class="tab-content" id="tab-rearrange">
        <div class="rearrange-panel">
            <h2>Piano Roll Editor - Logic Style</h2>

            <div id="rearrange-drop-zone">
                <p><strong>Drop audio or MIDI file here to edit</strong></p>
                <p style="font-size: 0.85rem; color: #888; margin-top: 8px">Supports: MP3, WAV, MIDI</p>
                <p style="font-size: 0.75rem; color: #666; margin-top: 5px">Audio files will be converted to MIDI for editing</p>
                <div class="spinner" id="convert-spinner"></div>
                <input type="file" id="rearrange-file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            </div>

            <div class="rearrange-toolbar">
                <div class="toolbar-group">
                    <span class="toolbar-label">Zoom:</span>
                    <input type="range" id="zoom-x" min="10" max="100" value="40" title="Horizontal zoom">
                    <input type="range" id="zoom-y" min="10" max="30" value="15" title="Vertical zoom">
                </div>
                <div class="toolbar-group">
                    <span class="toolbar-label">Snap:</span>
                    <select id="snap-select">
                        <option value="0">Off</option>
                        <option value="0.25">1/16</option>
                        <option value="0.5" selected>1/8</option>
                        <option value="1">1/4</option>
                    </select>
                </div>
                <div class="toolbar-group">
                    <button id="undo-btn" disabled>Undo</button>
                    <button id="clear-btn" disabled>Clear</button>
                    <button id="export-midi-btn" disabled>Export MIDI</button>
                    <button id="save-btn" class="secondary" disabled>Save Audio</button>
                </div>
            </div>

            <!-- Playback controls -->
            <div class="playback-controls">
                <button id="rearrange-play-btn" disabled>Play</button>
                <button id="rearrange-stop-btn" disabled>Stop</button>
                <span class="playback-time" id="rearrange-time">0:00 / 0:00</span>
                <input type="range" class="playback-slider" id="rearrange-slider" min="0" max="100" value="0" disabled>
            </div>

            <div class="piano-roll-wrapper">
                <div class="piano-roll-container">
                    <div class="piano-keys" id="piano-keys"></div>
                    <canvas id="piano-roll-canvas" width="1200" height="500"></canvas>
                </div>
            </div>

            <!-- Track list (Logic-like) -->
            <div class="track-list" id="track-list">
                <p style="color: #666; text-align: center; padding: 20px;">Load a file to see tracks</p>
            </div>

            <div class="status-bar">
                <span id="note-count">0 notes</span>
                <span id="tempo-info">-- BPM</span>
                <span id="selection-info">No selection</span>
                <span id="cursor-info">-</span>
            </div>

            <div class="help-text">
                <strong>Controls:</strong>
                Drag note horizontally = change time |
                Drag note vertically = change pitch |
                <kbd>Delete</kbd> or Right-click = remove note |
                <kbd>Ctrl+Z</kbd> = undo |
                <kbd>Space</kbd> = play/pause |
                Mouse wheel = scroll
            </div>
        </div>
    </div>

    <!-- Save Dialog -->
    <div class="save-dialog" id="save-dialog">
        <div class="save-dialog-content">
            <h3>Save Audio</h3>
            <p style="color: #888; margin-bottom: 15px;">Export your edited arrangement as an audio file</p>

            <div class="save-option">
                <input type="radio" name="save-format" id="save-wav" value="wav" checked>
                <label for="save-wav">WAV (Uncompressed, best quality)</label>
            </div>
            <div class="save-option">
                <input type="radio" name="save-format" id="save-mp3" value="mp3">
                <label for="save-mp3">MP3 (Compressed, smaller file)</label>
            </div>

            <div class="save-dialog-buttons">
                <button id="save-confirm-btn" class="secondary">Save</button>
                <button id="save-cancel-btn" style="background: #555;">Cancel</button>
            </div>

            <div class="spinner" id="save-spinner" style="margin-top: 15px;"></div>
            <p id="save-status" style="color: #888; text-align: center; margin-top: 10px;"></p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/tone@14/build/Tone.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@tonejs/midi@2/dist/Midi.min.js"></script>
    <script>
        // ============================================
        // TAB SWITCHING
        // ============================================
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });

        // ============================================
        // PLAYER TAB (Original functionality)
        // ============================================
        let currentAudio = null;
        let midiData = null;
        let synths = [];
        let isPlaying = false;

        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const playBtn = document.getElementById('play-btn');
        const stopBtn = document.getElementById('stop-btn');
        const progress = document.getElementById('progress');
        const currentTimeEl = document.getElementById('current-time');
        const totalTimeEl = document.getElementById('total-time');
        const fileInfo = document.getElementById('file-info');
        const volumeSlider = document.getElementById('volume');

        function setActiveStage(stage) {
            document.querySelectorAll('.stage').forEach(s => s.classList.remove('active'));
            if (stage) {
                document.getElementById('stage-' + stage).classList.add('active');
            }
        }

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins + ':' + secs.toString().padStart(2, '0');
        }

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handlePlayerFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', (e) => handlePlayerFile(e.target.files[0]));

        async function handlePlayerFile(file) {
            if (!file) return;
            stopPlayback();
            fileInfo.textContent = 'Loading: ' + file.name;

            if (file.name.includes('melody')) setActiveStage('melody');
            else if (file.name.includes('arrangement')) setActiveStage('arrangement');
            else if (file.name.includes('production')) setActiveStage('production');

            if (file.name.endsWith('.mid') || file.name.endsWith('.midi')) {
                const arrayBuffer = await file.arrayBuffer();
                midiData = new Midi(arrayBuffer);
                currentAudio = null;
                totalTimeEl.textContent = formatTime(midiData.duration);
                fileInfo.textContent = `MIDI: ${file.name} | ${midiData.tracks.length} tracks | ${formatTime(midiData.duration)}`;
            } else {
                const url = URL.createObjectURL(file);
                currentAudio = new Audio(url);
                currentAudio.volume = volumeSlider.value / 100;
                midiData = null;

                currentAudio.addEventListener('loadedmetadata', () => {
                    totalTimeEl.textContent = formatTime(currentAudio.duration);
                    fileInfo.textContent = `Audio: ${file.name} | ${formatTime(currentAudio.duration)}`;
                });

                currentAudio.addEventListener('timeupdate', () => {
                    const pct = (currentAudio.currentTime / currentAudio.duration) * 100;
                    progress.style.width = pct + '%';
                    currentTimeEl.textContent = formatTime(currentAudio.currentTime);
                });

                currentAudio.addEventListener('ended', () => {
                    isPlaying = false;
                    playBtn.textContent = 'Play';
                });
            }

            playBtn.disabled = false;
            stopBtn.disabled = false;
            document.getElementById('player-clear-btn').disabled = false;
        }

        volumeSlider.addEventListener('input', () => {
            if (currentAudio) currentAudio.volume = volumeSlider.value / 100;
        });

        playBtn.addEventListener('click', async () => {
            if (isPlaying) {
                if (currentAudio) currentAudio.pause();
                else if (midiData) Tone.Transport.pause();
                isPlaying = false;
                playBtn.textContent = 'Play';
            } else {
                if (currentAudio) currentAudio.play();
                else if (midiData) await playMidi();
                isPlaying = true;
                playBtn.textContent = 'Pause';
            }
        });

        stopBtn.addEventListener('click', stopPlayback);

        const playerClearBtn = document.getElementById('player-clear-btn');
        playerClearBtn.addEventListener('click', clearPlayer);

        function stopPlayback() {
            isPlaying = false;
            playBtn.textContent = 'Play';
            progress.style.width = '0%';
            currentTimeEl.textContent = '0:00';
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            }
            if (midiData) {
                Tone.Transport.stop();
                Tone.Transport.position = 0;
                synths.forEach(s => s.dispose());
                synths = [];
            }
        }

        function clearPlayer() {
            stopPlayback();
            currentAudio = null;
            midiData = null;
            synths = [];
            playBtn.disabled = true;
            stopBtn.disabled = true;
            playerClearBtn.disabled = true;
            totalTimeEl.textContent = '0:00';
            fileInfo.textContent = 'No file loaded';
            dropZone.innerHTML = `
                <p>Drop MIDI/WAV/MP3 file here</p>
                <p style="font-size: 0.8rem; color: #666; margin-top: 10px">or click to select</p>
                <input type="file" id="file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            `;
            const newFileInput = document.getElementById('file-input');
            dropZone.addEventListener('click', () => newFileInput.click());
            newFileInput.addEventListener('change', (e) => handlePlayerFile(e.target.files[0]));
            document.querySelectorAll('.stage').forEach(s => s.classList.remove('active'));
        }

        async function playMidi() {
            await Tone.start();
            synths.forEach(s => s.dispose());
            synths = [];

            midiData.tracks.forEach((track) => {
                const synth = new Tone.PolySynth(Tone.Synth, {
                    envelope: { attack: 0.02, decay: 0.1, sustain: 0.5, release: 0.3 }
                }).toDestination();
                synth.volume.value = -6;
                synths.push(synth);

                track.notes.forEach(note => {
                    Tone.Transport.schedule((time) => {
                        synth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
                    }, note.time);
                });
            });

            Tone.Transport.scheduleRepeat(() => {
                const pos = Tone.Transport.seconds;
                const pct = (pos / midiData.duration) * 100;
                progress.style.width = pct + '%';
                currentTimeEl.textContent = formatTime(pos);
            }, 0.1);

            Tone.Transport.start();
        }

        // ============================================
        // REARRANGE TAB - Piano Roll with Audio Support
        // ============================================
        const pianoRoll = {
            canvas: null,
            ctx: null,
            midiData: null,
            originalAudioFile: null,  // Keep reference to original audio
            notes: [],
            tracks: [],
            selectedNote: null,
            isDragging: false,
            dragStartX: 0,
            dragStartY: 0,
            originalNote: null,
            history: [],
            maxHistory: 50,

            // Display settings
            pixelsPerBeat: 40,
            noteHeight: 15,
            minPitch: 24,
            maxPitch: 96,
            scrollX: 0,
            scrollY: 0,
            snap: 0.5,
            tempo: 120,

            // Playback
            isPlaying: false,
            playbackPosition: 0,
            playbackSynths: [],
            scheduledNotes: [],

            // Track colors
            trackColors: [
                '#e94560', '#4ade80', '#60a5fa', '#f59e0b',
                '#a78bfa', '#ec4899', '#14b8a6', '#f97316',
            ],

            init() {
                this.canvas = document.getElementById('piano-roll-canvas');
                this.ctx = this.canvas.getContext('2d');
                this.setupPianoKeys();
                this.setupEventListeners();
                this.render();
            },

            setupPianoKeys() {
                const keysContainer = document.getElementById('piano-keys');
                keysContainer.innerHTML = '';

                const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

                for (let pitch = this.maxPitch; pitch >= this.minPitch; pitch--) {
                    const noteName = noteNames[pitch % 12];
                    const octave = Math.floor(pitch / 12) - 1;
                    const isBlack = noteName.includes('#');

                    const key = document.createElement('div');
                    key.className = 'piano-key ' + (isBlack ? 'black' : 'white');
                    key.textContent = noteName === 'C' ? `C${octave}` : '';
                    key.style.height = this.noteHeight + 'px';
                    keysContainer.appendChild(key);
                }
            },

            setupEventListeners() {
                const dropZone = document.getElementById('rearrange-drop-zone');
                const fileInput = document.getElementById('rearrange-file-input');

                dropZone.addEventListener('click', () => fileInput.click());
                dropZone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    dropZone.classList.add('drag-over');
                });
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
                dropZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('drag-over');
                    this.loadFile(e.dataTransfer.files[0]);
                });
                fileInput.addEventListener('change', (e) => this.loadFile(e.target.files[0]));

                // Canvas events
                this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
                this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
                this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
                this.canvas.addEventListener('contextmenu', (e) => this.onRightClick(e));
                this.canvas.addEventListener('wheel', (e) => this.onWheel(e));

                // Keyboard
                document.addEventListener('keydown', (e) => this.onKeyDown(e));

                // Toolbar
                document.getElementById('zoom-x').addEventListener('input', (e) => {
                    this.pixelsPerBeat = parseInt(e.target.value);
                    this.render();
                });
                document.getElementById('zoom-y').addEventListener('input', (e) => {
                    this.noteHeight = parseInt(e.target.value);
                    this.setupPianoKeys();
                    this.render();
                });
                document.getElementById('snap-select').addEventListener('change', (e) => {
                    this.snap = parseFloat(e.target.value);
                });
                document.getElementById('undo-btn').addEventListener('click', () => this.undo());
                document.getElementById('clear-btn').addEventListener('click', () => this.clear());
                document.getElementById('export-midi-btn').addEventListener('click', () => this.exportMidi());
                document.getElementById('save-btn').addEventListener('click', () => this.showSaveDialog());

                // Playback controls
                document.getElementById('rearrange-play-btn').addEventListener('click', () => this.togglePlayback());
                document.getElementById('rearrange-stop-btn').addEventListener('click', () => this.stopPlayback());

                // Save dialog
                document.getElementById('save-cancel-btn').addEventListener('click', () => this.hideSaveDialog());
                document.getElementById('save-confirm-btn').addEventListener('click', () => this.saveAudio());
            },

            async loadFile(file) {
                if (!file) return;

                const dropZone = document.getElementById('rearrange-drop-zone');
                const spinner = document.getElementById('convert-spinner');

                const isAudio = file.name.endsWith('.mp3') || file.name.endsWith('.wav');
                const isMidi = file.name.endsWith('.mid') || file.name.endsWith('.midi');

                if (!isAudio && !isMidi) {
                    alert('Please select an MP3, WAV, or MIDI file');
                    return;
                }

                this.originalAudioFile = isAudio ? file : null;

                if (isAudio) {
                    // Convert audio to MIDI via server
                    dropZone.classList.add('converting');
                    dropZone.innerHTML = `<p>Converting audio to MIDI...</p><div class="spinner active"></div>`;

                    try {
                        const formData = new FormData();
                        formData.append('file', file);

                        const response = await fetch('/api/convert', {
                            method: 'POST',
                            body: formData
                        });

                        if (!response.ok) {
                            throw new Error('Conversion failed');
                        }

                        const data = await response.json();
                        this.loadMidiData(data);

                        dropZone.classList.remove('converting');
                        dropZone.classList.add('has-file');
                        dropZone.innerHTML = `<p>Loaded: ${file.name}</p><p style="font-size: 0.8rem; color: #4ade80">${this.notes.length} notes detected | ${data.tracks.length} tracks | ${data.header.tempos[0].bpm.toFixed(0)} BPM</p>`;

                    } catch (error) {
                        console.error('Conversion error:', error);
                        dropZone.classList.remove('converting');
                        dropZone.innerHTML = `<p style="color: #e94560;">Conversion failed: ${error.message}</p><p style="font-size: 0.8rem; color: #666; margin-top: 10px">Try a MIDI file instead</p>`;
                    }

                } else {
                    // Load MIDI directly
                    const arrayBuffer = await file.arrayBuffer();
                    const midi = new Midi(arrayBuffer);
                    this.loadMidiFromTonejs(midi, file.name);
                }
            },

            loadMidiData(data) {
                // Load from our JSON format (from audio conversion)
                this.notes = [];
                this.tracks = [];
                this.tempo = data.header.tempos[0]?.bpm || 120;

                data.tracks.forEach((track, trackIndex) => {
                    const trackInfo = {
                        index: trackIndex,
                        name: track.name || `Track ${trackIndex + 1}`,
                        color: track.color || this.trackColors[trackIndex % this.trackColors.length],
                        visible: true,
                        muted: false,
                        solo: false,
                        noteCount: track.notes.length
                    };
                    this.tracks.push(trackInfo);

                    track.notes.forEach((note, noteIndex) => {
                        this.notes.push({
                            id: `${trackIndex}-${noteIndex}`,
                            trackIndex: trackIndex,
                            pitch: note.midi,
                            startTime: note.time,
                            duration: note.duration,
                            velocity: Math.round(note.velocity * 127),
                            name: note.name
                        });
                    });
                });

                this.finishLoading();
            },

            loadMidiFromTonejs(midi, filename) {
                // Load from Tone.js MIDI parser
                this.midiData = midi;
                this.notes = [];
                this.tracks = [];
                this.tempo = midi.header.tempos[0]?.bpm || 120;

                midi.tracks.forEach((track, trackIndex) => {
                    const trackInfo = {
                        index: trackIndex,
                        name: track.name || `Track ${trackIndex + 1}`,
                        color: this.trackColors[trackIndex % this.trackColors.length],
                        visible: true,
                        muted: false,
                        solo: false,
                        noteCount: track.notes.length
                    };
                    this.tracks.push(trackInfo);

                    track.notes.forEach((note, noteIndex) => {
                        this.notes.push({
                            id: `${trackIndex}-${noteIndex}`,
                            trackIndex: trackIndex,
                            pitch: note.midi,
                            startTime: note.time,
                            duration: note.duration,
                            velocity: Math.round(note.velocity * 127),
                            name: note.name
                        });
                    });
                });

                const dropZone = document.getElementById('rearrange-drop-zone');
                dropZone.classList.add('has-file');
                dropZone.innerHTML = `<p>Loaded: ${filename}</p><p style="font-size: 0.8rem; color: #4ade80">${this.notes.length} notes | ${this.tracks.length} tracks</p>`;

                this.finishLoading();
            },

            finishLoading() {
                this.updateTrackList();
                this.updateStatus();

                // Enable buttons
                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = false;
                document.getElementById('export-midi-btn').disabled = false;
                document.getElementById('save-btn').disabled = false;
                document.getElementById('rearrange-play-btn').disabled = false;
                document.getElementById('rearrange-stop-btn').disabled = false;

                // Adjust view to fit notes
                if (this.notes.length > 0) {
                    const minPitch = Math.min(...this.notes.map(n => n.pitch));
                    const maxPitch = Math.max(...this.notes.map(n => n.pitch));
                    this.minPitch = Math.max(0, minPitch - 5);
                    this.maxPitch = Math.min(127, maxPitch + 5);
                    this.setupPianoKeys();
                }

                this.history = [];
                this.render();
            },

            updateTrackList() {
                const container = document.getElementById('track-list');
                container.innerHTML = '';

                this.tracks.forEach((track, i) => {
                    const item = document.createElement('div');
                    item.className = 'track-item' + (track.visible ? ' active' : '') + (track.muted ? ' muted' : '');

                    const trackNotes = this.notes.filter(n => n.trackIndex === i).length;

                    item.innerHTML = `
                        <span class="track-color" style="background: ${track.color}"></span>
                        <span class="track-name">${track.name}</span>
                        <span class="track-notes">${trackNotes} notes</span>
                        <button class="track-mute ${track.muted ? 'active' : ''}" data-track="${i}">M</button>
                        <button class="track-solo ${track.solo ? 'active' : ''}" data-track="${i}">S</button>
                    `;

                    // Toggle visibility
                    item.addEventListener('click', (e) => {
                        if (e.target.classList.contains('track-mute') || e.target.classList.contains('track-solo')) return;
                        track.visible = !track.visible;
                        item.classList.toggle('active');
                        this.render();
                    });

                    // Mute button
                    item.querySelector('.track-mute').addEventListener('click', (e) => {
                        e.stopPropagation();
                        track.muted = !track.muted;
                        e.target.classList.toggle('active');
                        item.classList.toggle('muted');
                    });

                    // Solo button
                    item.querySelector('.track-solo').addEventListener('click', (e) => {
                        e.stopPropagation();
                        track.solo = !track.solo;
                        e.target.classList.toggle('active');
                    });

                    container.appendChild(item);
                });
            },

            updateStatus() {
                document.getElementById('note-count').textContent = `${this.notes.length} notes`;
                document.getElementById('tempo-info').textContent = `${this.tempo.toFixed(0)} BPM`;
            },

            saveToHistory() {
                const state = JSON.stringify(this.notes);
                this.history.push(state);
                if (this.history.length > this.maxHistory) {
                    this.history.shift();
                }
                document.getElementById('undo-btn').disabled = false;
            },

            undo() {
                if (this.history.length === 0) return;
                this.notes = JSON.parse(this.history.pop());
                this.updateStatus();
                this.render();
                document.getElementById('undo-btn').disabled = this.history.length === 0;
            },

            clear() {
                this.stopPlayback();
                this.midiData = null;
                this.originalAudioFile = null;
                this.notes = [];
                this.tracks = [];
                this.selectedNote = null;
                this.history = [];

                const dropZone = document.getElementById('rearrange-drop-zone');
                dropZone.classList.remove('has-file', 'converting');
                dropZone.innerHTML = `
                    <p><strong>Drop audio or MIDI file here to edit</strong></p>
                    <p style="font-size: 0.85rem; color: #888; margin-top: 8px">Supports: MP3, WAV, MIDI</p>
                    <p style="font-size: 0.75rem; color: #666; margin-top: 5px">Audio files will be converted to MIDI for editing</p>
                    <input type="file" id="rearrange-file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
                `;

                const fileInput = document.getElementById('rearrange-file-input');
                dropZone.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', (e) => this.loadFile(e.target.files[0]));

                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = true;
                document.getElementById('export-midi-btn').disabled = true;
                document.getElementById('save-btn').disabled = true;
                document.getElementById('rearrange-play-btn').disabled = true;
                document.getElementById('rearrange-stop-btn').disabled = true;

                document.getElementById('track-list').innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">Load a file to see tracks</p>';
                document.getElementById('note-count').textContent = '0 notes';
                document.getElementById('tempo-info').textContent = '-- BPM';
                document.getElementById('selection-info').textContent = 'No selection';

                this.render();
            },

            render() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                ctx.fillStyle = '#111';
                ctx.fillRect(0, 0, width, height);

                this.drawGrid();

                // Get visible tracks (considering solo)
                const hasSolo = this.tracks.some(t => t.solo);
                const visibleTracks = this.tracks
                    .filter(t => t.visible && !t.muted && (hasSolo ? t.solo : true))
                    .map(t => t.index);

                this.notes.forEach(note => {
                    if (!visibleTracks.includes(note.trackIndex)) return;

                    const x = note.startTime * this.pixelsPerBeat - this.scrollX;
                    const y = (this.maxPitch - note.pitch) * this.noteHeight - this.scrollY;
                    const w = Math.max(4, note.duration * this.pixelsPerBeat);
                    const h = this.noteHeight - 2;

                    if (x + w < 0 || x > width || y + h < 0 || y > height) return;

                    const track = this.tracks[note.trackIndex];
                    ctx.fillStyle = note === this.selectedNote ? '#fff' : track.color;
                    ctx.fillRect(x, y, w, h);

                    ctx.strokeStyle = note === this.selectedNote ? '#e94560' : 'rgba(0,0,0,0.5)';
                    ctx.lineWidth = note === this.selectedNote ? 2 : 1;
                    ctx.strokeRect(x, y, w, h);

                    if (w > 30) {
                        ctx.fillStyle = note === this.selectedNote ? '#000' : '#fff';
                        ctx.font = '10px sans-serif';
                        ctx.fillText(note.name || '', x + 3, y + h - 4);
                    }
                });

                // Draw playhead
                if (this.playbackPosition > 0) {
                    const playheadX = this.playbackPosition * this.pixelsPerBeat - this.scrollX;
                    ctx.strokeStyle = '#4ade80';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(playheadX, 0);
                    ctx.lineTo(playheadX, height);
                    ctx.stroke();
                }
            },

            drawGrid() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                // Horizontal lines (pitch)
                for (let pitch = this.minPitch; pitch <= this.maxPitch; pitch++) {
                    const y = (this.maxPitch - pitch) * this.noteHeight - this.scrollY;
                    if (y < 0 || y > height) continue;

                    ctx.strokeStyle = pitch % 12 === 0 ? '#333' : '#1a1a1a';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(width, y);
                    ctx.stroke();
                }

                // Vertical lines (beats)
                const maxTime = this.notes.length > 0
                    ? Math.max(...this.notes.map(n => n.startTime + n.duration)) + 4
                    : 60;

                for (let beat = 0; beat <= maxTime; beat += 0.25) {
                    const x = beat * this.pixelsPerBeat - this.scrollX;
                    if (x < 0 || x > width) continue;

                    if (beat % 4 === 0) {
                        ctx.strokeStyle = '#444';
                    } else if (beat % 1 === 0) {
                        ctx.strokeStyle = '#2a2a2a';
                    } else {
                        ctx.strokeStyle = '#1a1a1a';
                    }

                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                }
            },

            getNoteAt(x, y) {
                const hasSolo = this.tracks.some(t => t.solo);
                const visibleTracks = this.tracks
                    .filter(t => t.visible && !t.muted && (hasSolo ? t.solo : true))
                    .map(t => t.index);

                for (let i = this.notes.length - 1; i >= 0; i--) {
                    const note = this.notes[i];
                    if (!visibleTracks.includes(note.trackIndex)) continue;

                    const nx = note.startTime * this.pixelsPerBeat - this.scrollX;
                    const ny = (this.maxPitch - note.pitch) * this.noteHeight - this.scrollY;
                    const nw = Math.max(4, note.duration * this.pixelsPerBeat);
                    const nh = this.noteHeight - 2;

                    if (x >= nx && x <= nx + nw && y >= ny && y <= ny + nh) {
                        return note;
                    }
                }
                return null;
            },

            onMouseDown(e) {
                const rect = this.canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const note = this.getNoteAt(x, y);

                if (note) {
                    this.selectedNote = note;
                    this.isDragging = true;
                    this.dragStartX = x;
                    this.dragStartY = y;
                    this.originalNote = { ...note };
                    this.canvas.style.cursor = 'grabbing';
                    document.getElementById('selection-info').textContent =
                        `Selected: ${note.name} (t=${note.startTime.toFixed(2)}, v=${note.velocity})`;
                } else {
                    this.selectedNote = null;
                    document.getElementById('selection-info').textContent = 'No selection';
                }

                this.render();
            },

            onMouseMove(e) {
                const rect = this.canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const beat = (x + this.scrollX) / this.pixelsPerBeat;
                const pitch = Math.round(this.maxPitch - (y + this.scrollY) / this.noteHeight);
                const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
                const noteName = noteNames[((pitch % 12) + 12) % 12] + Math.floor(pitch / 12 - 1);
                document.getElementById('cursor-info').textContent = `Beat: ${beat.toFixed(2)} | ${noteName}`;

                if (this.isDragging && this.selectedNote) {
                    const dx = x - this.dragStartX;
                    const dy = y - this.dragStartY;

                    let newTime = this.originalNote.startTime + dx / this.pixelsPerBeat;
                    let newPitch = this.originalNote.pitch - Math.round(dy / this.noteHeight);

                    if (this.snap > 0) {
                        newTime = Math.round(newTime / this.snap) * this.snap;
                    }

                    newTime = Math.max(0, newTime);
                    newPitch = Math.max(0, Math.min(127, newPitch));

                    this.selectedNote.startTime = newTime;
                    this.selectedNote.pitch = newPitch;
                    this.selectedNote.name = noteNames[((newPitch % 12) + 12) % 12] + Math.floor(newPitch / 12 - 1);

                    document.getElementById('selection-info').textContent =
                        `Moving: ${this.selectedNote.name} (t=${newTime.toFixed(2)})`;

                    this.render();
                } else {
                    const note = this.getNoteAt(x, y);
                    this.canvas.style.cursor = note ? 'grab' : 'default';
                }
            },

            onMouseUp(e) {
                if (this.isDragging && this.selectedNote) {
                    if (this.selectedNote.startTime !== this.originalNote.startTime ||
                        this.selectedNote.pitch !== this.originalNote.pitch) {
                        this.saveToHistory();
                    }
                }

                this.isDragging = false;
                this.canvas.style.cursor = 'default';
            },

            onRightClick(e) {
                e.preventDefault();

                const rect = this.canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const note = this.getNoteAt(x, y);
                if (note) {
                    this.deleteNote(note);
                }
            },

            onKeyDown(e) {
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    if (this.selectedNote) {
                        this.deleteNote(this.selectedNote);
                    }
                } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.undo();
                } else if (e.key === ' ') {
                    e.preventDefault();
                    this.togglePlayback();
                }
            },

            onWheel(e) {
                e.preventDefault();

                if (e.shiftKey) {
                    this.scrollX += e.deltaY;
                } else {
                    this.scrollY += e.deltaY;
                }

                this.scrollX = Math.max(0, this.scrollX);
                this.scrollY = Math.max(0, this.scrollY);

                this.render();
            },

            deleteNote(note) {
                this.saveToHistory();
                const index = this.notes.indexOf(note);
                if (index > -1) {
                    this.notes.splice(index, 1);
                    this.selectedNote = null;
                    this.updateStatus();
                    this.updateTrackList();
                    document.getElementById('selection-info').textContent = 'Note deleted';
                    this.render();
                }
            },

            // Playback with Tone.js
            async togglePlayback() {
                if (this.isPlaying) {
                    this.pausePlayback();
                } else {
                    await this.startPlayback();
                }
            },

            async startPlayback() {
                await Tone.start();

                this.isPlaying = true;
                document.getElementById('rearrange-play-btn').textContent = 'Pause';

                // Dispose old synths
                this.playbackSynths.forEach(s => s.dispose());
                this.playbackSynths = [];

                // Create synths for each track
                const hasSolo = this.tracks.some(t => t.solo);

                this.tracks.forEach((track, i) => {
                    const synth = new Tone.PolySynth(Tone.Synth, {
                        envelope: { attack: 0.02, decay: 0.1, sustain: 0.5, release: 0.3 }
                    }).toDestination();

                    // Apply mute/solo
                    const shouldPlay = !track.muted && (hasSolo ? track.solo : true);
                    synth.volume.value = shouldPlay ? -6 : -Infinity;

                    this.playbackSynths.push(synth);

                    // Schedule notes for this track
                    const trackNotes = this.notes.filter(n => n.trackIndex === i);
                    trackNotes.forEach(note => {
                        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
                        const noteName = noteNames[note.pitch % 12] + Math.floor(note.pitch / 12 - 1);

                        Tone.Transport.schedule((time) => {
                            synth.triggerAttackRelease(noteName, note.duration, time, note.velocity / 127);
                        }, note.startTime);
                    });
                });

                // Update playhead
                const maxTime = this.notes.length > 0
                    ? Math.max(...this.notes.map(n => n.startTime + n.duration))
                    : 10;

                Tone.Transport.scheduleRepeat((time) => {
                    this.playbackPosition = Tone.Transport.seconds;
                    const pct = (this.playbackPosition / maxTime) * 100;
                    document.getElementById('rearrange-slider').value = pct;
                    document.getElementById('rearrange-time').textContent =
                        `${formatTime(this.playbackPosition)} / ${formatTime(maxTime)}`;
                    this.render();

                    if (this.playbackPosition >= maxTime) {
                        this.stopPlayback();
                    }
                }, 0.05);

                Tone.Transport.start();
            },

            pausePlayback() {
                this.isPlaying = false;
                document.getElementById('rearrange-play-btn').textContent = 'Play';
                Tone.Transport.pause();
            },

            stopPlayback() {
                this.isPlaying = false;
                this.playbackPosition = 0;
                document.getElementById('rearrange-play-btn').textContent = 'Play';
                document.getElementById('rearrange-time').textContent = '0:00 / 0:00';
                document.getElementById('rearrange-slider').value = 0;

                Tone.Transport.stop();
                Tone.Transport.cancel();

                this.playbackSynths.forEach(s => s.dispose());
                this.playbackSynths = [];

                this.render();
            },

            exportMidi() {
                if (this.notes.length === 0) return;

                const newMidi = new Midi();
                newMidi.header.setTempo(this.tempo);

                this.tracks.forEach((trackInfo, trackIndex) => {
                    const track = newMidi.addTrack();
                    track.name = trackInfo.name;

                    const trackNotes = this.notes.filter(n => n.trackIndex === trackIndex);
                    trackNotes.forEach(note => {
                        track.addNote({
                            midi: note.pitch,
                            time: note.startTime,
                            duration: note.duration,
                            velocity: note.velocity / 127
                        });
                    });
                });

                const blob = new Blob([newMidi.toArray()], { type: 'audio/midi' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'rearranged.mid';
                a.click();
                URL.revokeObjectURL(url);
            },

            showSaveDialog() {
                document.getElementById('save-dialog').classList.add('active');
            },

            hideSaveDialog() {
                document.getElementById('save-dialog').classList.remove('active');
                document.getElementById('save-spinner').classList.remove('active');
                document.getElementById('save-status').textContent = '';
            },

            async saveAudio() {
                const format = document.querySelector('input[name="save-format"]:checked').value;
                const spinner = document.getElementById('save-spinner');
                const status = document.getElementById('save-status');

                spinner.classList.add('active');
                status.textContent = 'Rendering audio...';

                try {
                    // Create MIDI blob
                    const newMidi = new Midi();
                    newMidi.header.setTempo(this.tempo);

                    this.tracks.forEach((trackInfo, trackIndex) => {
                        const track = newMidi.addTrack();
                        track.name = trackInfo.name;

                        const trackNotes = this.notes.filter(n => n.trackIndex === trackIndex);
                        trackNotes.forEach(note => {
                            track.addNote({
                                midi: note.pitch,
                                time: note.startTime,
                                duration: note.duration,
                                velocity: note.velocity / 127
                            });
                        });
                    });

                    // Send to server for rendering
                    const midiBlob = new Blob([newMidi.toArray()], { type: 'audio/midi' });
                    const formData = new FormData();
                    formData.append('midi', midiBlob, 'arrangement.mid');
                    formData.append('format', format);

                    const response = await fetch('/api/render', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(errorText || 'Render failed');
                    }

                    // Download the rendered audio
                    const audioBlob = await response.blob();
                    const url = URL.createObjectURL(audioBlob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `rearranged.${format}`;
                    a.click();
                    URL.revokeObjectURL(url);

                    status.textContent = 'Audio saved!';
                    setTimeout(() => this.hideSaveDialog(), 1500);

                } catch (error) {
                    console.error('Save error:', error);
                    status.textContent = `Error: ${error.message}`;
                    status.style.color = '#e94560';
                    spinner.classList.remove('active');
                }
            }
        };

        // Initialize piano roll when page loads
        pianoRoll.init();
    </script>
</body>
</html>
"""


class PlayerHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with API endpoints for audio conversion and rendering."""

    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/' or self.path == '/player.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(BROWSER_PLAYER_V2_HTML.encode())
        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests for API endpoints."""
        parsed = urlparse(self.path)

        if parsed.path == '/api/convert':
            self.handle_convert()
        elif parsed.path == '/api/render':
            self.handle_render()
        else:
            self.send_error(404, 'Not found')

    def handle_convert(self):
        """Convert uploaded audio to MIDI."""
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_error(400, 'Expected multipart/form-data')
                return

            # Parse multipart data
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Extract boundary
            boundary = content_type.split('boundary=')[1].encode()

            # Parse file from multipart
            parts = body.split(b'--' + boundary)
            file_data = None
            filename = 'audio'

            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    header_end = part.find(b'\r\n\r\n')
                    headers = part[:header_end].decode('utf-8', errors='ignore')
                    for line in headers.split('\r\n'):
                        if 'filename=' in line:
                            filename = line.split('filename=')[1].strip('"\'')

                    # Extract file content
                    file_data = part[header_end + 4:].rstrip(b'\r\n--')
                    break

            if not file_data:
                self.send_error(400, 'No file uploaded')
                return

            # Save to temp file
            suffix = Path(filename).suffix or '.mp3'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(file_data)
                temp_path = f.name

            try:
                # Convert to MIDI
                json_result = audio_to_midi_json(temp_path)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json_result.encode())

            finally:
                os.unlink(temp_path)

        except Exception as e:
            print(f"Convert error: {e}")
            import traceback
            traceback.print_exc()
            self.send_error(500, str(e))

    def handle_render(self):
        """Render MIDI to audio."""
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_error(400, 'Expected multipart/form-data')
                return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Parse multipart
            boundary = content_type.split('boundary=')[1].encode()
            parts = body.split(b'--' + boundary)

            midi_data = None
            output_format = 'wav'

            for part in parts:
                if b'Content-Disposition' in part:
                    header_end = part.find(b'\r\n\r\n')
                    headers = part[:header_end].decode('utf-8', errors='ignore')

                    if 'name="midi"' in headers:
                        midi_data = part[header_end + 4:].rstrip(b'\r\n--')
                    elif 'name="format"' in headers:
                        output_format = part[header_end + 4:].rstrip(b'\r\n--').decode()

            if not midi_data:
                self.send_error(400, 'No MIDI data')
                return

            # Save MIDI to temp
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
                f.write(midi_data)
                midi_path = f.name

            output_path = tempfile.mktemp(suffix=f'.{output_format}')

            try:
                # Try FluidSynth first
                if midi_to_audio(midi_path, output_path, output_format):
                    with open(output_path, 'rb') as f:
                        audio_data = f.read()

                    content_type = 'audio/wav' if output_format == 'wav' else 'audio/mpeg'
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Disposition', f'attachment; filename="rearranged.{output_format}"')
                    self.end_headers()
                    self.wfile.write(audio_data)
                else:
                    self.send_error(500, 'FluidSynth not available. Install FluidSynth and a SoundFont to enable audio export.')

            finally:
                if os.path.exists(midi_path):
                    os.unlink(midi_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()
            self.send_error(500, str(e))


def create_player_v2(output_dir: str | Path) -> str:
    """Create player HTML file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    player_path = output_dir / "player.html"
    with open(player_path, "w", encoding="utf-8") as f:
        f.write(BROWSER_PLAYER_V2_HTML)

    return str(player_path)


def serve_player_v2(port: int = 8765) -> threading.Thread:
    """Start player server."""
    handler = lambda *args, **kwargs: PlayerHandler(*args, directory=tempfile.gettempdir(), **kwargs)

    def serve():
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread


def play_with_rearrange_v2(port: int = 8765) -> PlaybackResult:
    """Open browser player with Rearrange v2."""
    serve_player_v2(port)

    url = f"http://localhost:{port}/player.html"
    webbrowser.open(url)

    return PlaybackResult(
        success=True,
        method=PlaybackMethod.BROWSER,
        message=f"Rearrange v2 player opened at {url}"
    )


if __name__ == "__main__":
    print("Starting Rearrange Player v2...")
    print("Features:")
    print("  - Load MP3/WAV files (auto-convert to MIDI)")
    print("  - Edit notes in piano roll")
    print("  - Save as MP3/WAV (requires FluidSynth)")
    print()

    result = play_with_rearrange_v2()
    print(f"Result: {result.message}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped.")
