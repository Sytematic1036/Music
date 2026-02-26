"""
Extended player module with Rearrange tab - Version 3.

MAJOR CHANGE from v2:
- v2 converted audio to MIDI (poor quality)
- v3 finds and uses ORIGINAL MIDI files (perfect quality)

When user opens production.mp3, we find 02_arrangement.mid and use that.
Sound quality is now identical to Player tab.
"""

import http.server
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
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class PlaybackMethod(Enum):
    BROWSER = "browser"
    PYTHON = "python"
    EXPORT = "export"


@dataclass
class PlaybackResult:
    success: bool
    method: PlaybackMethod
    message: str = ""
    file_path: Optional[str] = None


def find_source_midi(audio_path: str | Path) -> Optional[Path]:
    """
    Find the original MIDI file that was used to create the audio file.

    Search strategy:
    1. Same directory: look for .mid files
    2. Parent directory: look for 01_melody.mid, 02_arrangement.mid
    3. Sibling directories: ../01_melody/, ../02_arrangement/

    Returns:
        Path to MIDI file, or None if not found
    """
    audio_path = Path(audio_path)
    audio_dir = audio_path.parent
    audio_name = audio_path.stem.lower()

    # Priority order for MIDI files
    midi_patterns = [
        # Same directory
        audio_dir / f"{audio_path.stem}.mid",
        audio_dir / f"{audio_path.stem}.midi",
        # Parent directory - arrangement (multi-track, best)
        audio_dir.parent / "02_arrangement.mid",
        audio_dir.parent / "arrangement.mid",
        # Parent directory - melody (single track)
        audio_dir.parent / "01_melody.mid",
        audio_dir.parent / "melody.mid",
        # Any MIDI in parent
        audio_dir.parent / "*.mid",
    ]

    for pattern in midi_patterns:
        if "*" in str(pattern):
            # Glob pattern
            matches = list(pattern.parent.glob(pattern.name))
            if matches:
                # Prefer arrangement over melody
                for match in matches:
                    if "arrangement" in match.stem.lower():
                        return match
                for match in matches:
                    if "melody" in match.stem.lower():
                        return match
                return matches[0]
        elif pattern.exists():
            return pattern

    # Search recursively in parent directories (up to 3 levels)
    search_dir = audio_dir
    for _ in range(3):
        search_dir = search_dir.parent
        if not search_dir.exists():
            break

        # Look for any .mid files
        midi_files = list(search_dir.glob("*.mid")) + list(search_dir.glob("**/*.mid"))
        if midi_files:
            # Prefer arrangement
            for f in midi_files:
                if "arrangement" in f.stem.lower():
                    return f
            for f in midi_files:
                if "melody" in f.stem.lower():
                    return f
            return midi_files[0]

    return None


def check_fluidsynth() -> bool:
    """Check if FluidSynth is available."""
    try:
        result = subprocess.run(["fluidsynth", "-V"], capture_output=True, timeout=5)
        return b"FluidSynth" in result.stdout or b"FluidSynth" in result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def find_soundfont() -> Optional[str]:
    """Find a SoundFont file for FluidSynth."""
    locations = [
        "C:/soundfonts/FluidR3_GM.sf2",
        "C:/Program Files/FluidSynth/share/soundfonts/default.sf2",
        os.path.expanduser("~/soundfonts/FluidR3_GM.sf2"),
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    ]
    for loc in locations:
        if os.path.exists(loc):
            return loc
    return None


def apply_production_effects(input_wav: str | Path, output_wav: str | Path) -> bool:
    """
    Apply same audio effects as production.py for matching sound quality.

    Effects (RELAXATION preset):
    - Volume: 0.8
    - Bass: -2dB (less muddy)
    - Mid: +1dB (clearer)
    - Treble: +2dB (brighter)
    - Compression: -12dB threshold, 4:1 ratio
    - Reverb: 0.25 amount, 1.5s decay
    - Stereo width: 1.1
    - Limiter: 0.95
    """
    # RELAXATION preset from production.py
    filters = [
        "volume=0.8",
        "lowshelf=f=200:g=-2.0",      # bass_boost
        "equalizer=f=1000:width_type=o:width=2:g=1.0",  # mid_boost
        "highshelf=f=3000:g=2.0",     # treble_boost
        "acompressor=threshold=-12dB:ratio=4:attack=20:release=250",
        "aecho=0.8:0.9:150:0.25",     # reverb (delay=150ms, decay=0.25)
        "stereotools=mlev=1.1",       # stereo width
        "alimiter=limit=0.95:attack=5:release=50"
    ]

    filter_string = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_wav),
        "-af", filter_string,
        str(output_wav)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"Effects error: {e}")
        return False


def midi_to_audio(midi_path: str | Path, output_path: str | Path, format: str = "wav", apply_effects: bool = True) -> bool:
    """Convert MIDI to audio using FluidSynth + production effects."""
    if not check_fluidsynth():
        return False

    soundfont = find_soundfont()
    if not soundfont:
        return False

    midi_path = Path(midi_path)
    output_path = Path(output_path)

    # Render to temporary WAV first
    raw_wav = output_path.with_suffix(".raw.wav")
    final_wav = output_path if format == "wav" else output_path.with_suffix(".wav")

    # Use gain=1.5 to avoid clipping (gain=5.0 caused distortion)
    cmd = ["fluidsynth", "-ni", "-g", "1.5", "-F", str(raw_wav), soundfont, str(midi_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return False

        # Apply production effects
        if apply_effects:
            if not apply_production_effects(raw_wav, final_wav):
                # Fallback to raw if effects fail
                import shutil
                shutil.copy(raw_wav, final_wav)
            # Clean up raw file
            if raw_wav.exists():
                raw_wav.unlink()
        else:
            # Just rename raw to final
            if raw_wav.exists():
                raw_wav.rename(final_wav)

        # Convert to MP3 if requested
        if format == "mp3" and final_wav.exists():
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(final_wav), "-b:a", "320k", str(output_path)],
                    capture_output=True, timeout=60
                )
                final_wav.unlink()
            except:
                pass

        return output_path.exists()
    except subprocess.TimeoutExpired:
        return False


# HTML template - v3 with original MIDI support
BROWSER_PLAYER_V3_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Player - EXP-004 v3 Rearrange</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
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
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
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
        .tab:hover { background: rgba(255,255,255,0.15); color: #fff; }
        .tab.active {
            background: rgba(233,69,96,0.3);
            color: #e94560;
            border-bottom: 2px solid #e94560;
        }
        .tab-content { display: none; width: 100%; max-width: 1400px; }
        .tab-content.active { display: block; }

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
        h1, h2 { font-size: 1.5rem; margin-bottom: 10px; color: #e94560; }

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
        .stage h3 { color: #e94560; margin-bottom: 5px; }

        .controls { display: flex; justify-content: center; gap: 15px; margin: 30px 0; flex-wrap: wrap; }

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
        button:hover { background: #ff6b6b; transform: scale(1.05); }
        button:disabled { background: #555; cursor: not-allowed; transform: none; }
        button.secondary { background: #4ade80; }
        button.secondary:hover { background: #22c55e; }

        .progress { background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; margin: 20px 0; overflow: hidden; }
        .progress-bar { background: #e94560; height: 100%; width: 0%; transition: width 0.1s; }
        .time { font-size: 0.9rem; color: #aaa; }
        .file-info { margin-top: 20px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px; font-size: 0.85rem; color: #888; }

        #drop-zone, #rearrange-drop-zone {
            border: 2px dashed #555;
            border-radius: 10px;
            padding: 40px;
            margin: 20px 0;
            transition: all 0.3s;
            cursor: pointer;
        }
        #drop-zone:hover, #rearrange-drop-zone:hover { border-color: #888; }
        .drag-over { border-color: #e94560 !important; background: rgba(233,69,96,0.1) !important; }
        .has-file { border-color: #4ade80 !important; background: rgba(74,222,128,0.1) !important; }

        .volume-control { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 20px; }
        input[type="range"] { width: 150px; }

        /* Rearrange Panel */
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
        .toolbar-group { display: flex; gap: 10px; align-items: center; }
        .toolbar-label { color: #aaa; font-size: 0.85rem; }

        .piano-roll-container {
            position: relative;
            background: #111;
            border-radius: 10px;
            overflow: hidden;
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
        .piano-key.black { background: #1a1a1a; }
        .piano-key.white { background: #2a2a2a; }
        #piano-roll-canvas { display: block; margin-left: 50px; cursor: default; }

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
        .track-item:hover { background: rgba(255,255,255,0.1); }
        .track-item.active { background: rgba(233,69,96,0.2); border-left: 3px solid #e94560; }
        .track-item .track-color { width: 16px; height: 16px; border-radius: 3px; }
        .track-item .track-name { flex: 1; font-weight: 500; }
        .track-item .track-notes { color: #888; font-size: 0.85rem; }

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

        .playback-controls {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
        }
        .playback-time { font-family: monospace; color: #4ade80; font-size: 1.2rem; }

        .help-text {
            margin-top: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            font-size: 0.8rem;
            color: #666;
        }
        .help-text kbd { background: #333; padding: 2px 6px; border-radius: 3px; font-family: monospace; }

        /* Info banner */
        .info-banner {
            background: rgba(74,222,128,0.2);
            border: 1px solid #4ade80;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
        .info-banner.warning {
            background: rgba(245,158,11,0.2);
            border-color: #f59e0b;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #1a1a2e;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            width: 90%;
        }
        .modal h3 { color: #e94560; margin-bottom: 20px; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="tabs">
        <button class="tab active" data-tab="player">Player</button>
        <button class="tab" data-tab="rearrange">Rearrange</button>
    </div>

    <!-- Player Tab -->
    <div class="tab-content active" id="tab-player">
        <div class="player">
            <h1>Music Pipeline Player</h1>
            <div id="stages">
                <div class="stage" id="stage-melody"><h3>1. Melody</h3><p>Base melodic line</p></div>
                <div class="stage" id="stage-arrangement"><h3>2. Arrangement</h3><p>Multi-track instruments</p></div>
                <div class="stage" id="stage-production"><h3>3. Production</h3><p>Mixed & mastered audio</p></div>
            </div>
            <div id="drop-zone">
                <p>Drop MIDI/WAV/MP3 file here</p>
                <p style="font-size: 0.8rem; color: #666; margin-top: 10px">or click to select</p>
                <input type="file" id="file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            </div>
            <div class="progress"><div class="progress-bar" id="progress"></div></div>
            <div class="time"><span id="current-time">0:00</span> / <span id="total-time">0:00</span></div>
            <div class="controls">
                <button id="play-btn" disabled>Play</button>
                <button id="stop-btn" disabled>Stop</button>
                <button id="player-clear-btn" disabled>Clear</button>
            </div>
            <div class="volume-control">
                <span>Volume:</span>
                <input type="range" id="volume" min="0" max="100" value="80">
            </div>
            <div class="file-info" id="file-info">No file loaded</div>
        </div>
    </div>

    <!-- Rearrange Tab -->
    <div class="tab-content" id="tab-rearrange">
        <div class="rearrange-panel">
            <h2>Piano Roll Editor - v3</h2>

            <div class="info-banner">
                <strong>v3:</strong> Nu använder vi original MIDI-filer för bästa ljudkvalitet!
                <br>Dra en MP3/WAV så hittar vi automatiskt tillhörande MIDI.
            </div>

            <div id="rearrange-drop-zone">
                <p><strong>Drop MP3/WAV eller MIDI file here</strong></p>
                <p style="font-size: 0.85rem; color: #888; margin-top: 8px">
                    MP3/WAV → Vi hittar original MIDI automatiskt
                </p>
                <input type="file" id="rearrange-file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            </div>

            <div class="rearrange-toolbar">
                <div class="toolbar-group">
                    <span class="toolbar-label">Zoom:</span>
                    <input type="range" id="zoom-x" min="10" max="100" value="40" title="Horizontal">
                    <input type="range" id="zoom-y" min="10" max="30" value="15" title="Vertical">
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

            <div class="playback-controls">
                <button id="rearrange-play-btn" disabled>Play</button>
                <button id="rearrange-stop-btn" disabled>Stop</button>
                <span class="playback-time" id="rearrange-time">0:00 / 0:00</span>
            </div>

            <div class="piano-roll-container">
                <div class="piano-keys" id="piano-keys"></div>
                <canvas id="piano-roll-canvas" width="1200" height="500"></canvas>
            </div>

            <div class="track-list" id="track-list">
                <p style="color: #666; text-align: center; padding: 20px;">Load a file to see tracks</p>
            </div>

            <div class="status-bar">
                <span id="note-count">0 notes</span>
                <span id="midi-source">No MIDI loaded</span>
                <span id="selection-info">No selection</span>
            </div>

            <div class="help-text">
                <strong>Controls:</strong>
                Drag note = change time/pitch |
                <kbd>Delete</kbd> = remove note |
                <kbd>Ctrl+Z</kbd> = undo |
                <kbd>Space</kbd> = play/pause
            </div>
        </div>
    </div>

    <!-- MIDI Selection Modal -->
    <div class="modal" id="midi-modal">
        <div class="modal-content">
            <h3>Select MIDI Source</h3>
            <p id="midi-modal-message">No MIDI file found automatically.</p>
            <div id="midi-options"></div>
            <div class="modal-buttons">
                <button id="midi-browse-btn">Browse for MIDI...</button>
                <button id="midi-cancel-btn" style="background:#555">Cancel</button>
            </div>
            <input type="file" id="midi-file-picker" accept=".mid,.midi" style="display:none">
        </div>
    </div>

    <!-- Save Modal -->
    <div class="modal" id="save-modal">
        <div class="modal-content">
            <h3>Save Audio</h3>
            <p style="color:#888;margin-bottom:15px;">Export edited arrangement as audio</p>
            <div style="margin:10px 0;">
                <input type="radio" name="format" id="save-wav" value="wav" checked>
                <label for="save-wav">WAV (best quality)</label>
            </div>
            <div style="margin:10px 0;">
                <input type="radio" name="format" id="save-mp3" value="mp3">
                <label for="save-mp3">MP3 (smaller file)</label>
            </div>
            <div class="modal-buttons">
                <button id="save-confirm-btn" class="secondary">Save</button>
                <button id="save-cancel-btn" style="background:#555">Cancel</button>
            </div>
            <p id="save-status" style="color:#888;text-align:center;margin-top:10px;"></p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/tone@14/build/Tone.min.js"></script>
    <script src="https://unpkg.com/@tonejs/midi@2.0.28/build/Midi.js"></script>
    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });

        // ============================================
        // PLAYER TAB
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

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins + ':' + secs.toString().padStart(2, '0');
        }

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); handlePlayerFile(e.dataTransfer.files[0]); });
        fileInput.addEventListener('change', e => handlePlayerFile(e.target.files[0]));

        async function handlePlayerFile(file) {
            if (!file) return;
            stopPlayback();
            fileInfo.textContent = 'Loading: ' + file.name;

            if (file.name.endsWith('.mid') || file.name.endsWith('.midi')) {
                const arrayBuffer = await file.arrayBuffer();
                midiData = new Midi(arrayBuffer);
                currentAudio = null;
                totalTimeEl.textContent = formatTime(midiData.duration);
                fileInfo.textContent = `MIDI: ${file.name} | ${midiData.tracks.length} tracks`;
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
                    progress.style.width = (currentAudio.currentTime / currentAudio.duration * 100) + '%';
                    currentTimeEl.textContent = formatTime(currentAudio.currentTime);
                });
                currentAudio.addEventListener('ended', () => { isPlaying = false; playBtn.textContent = 'Play'; });
            }
            playBtn.disabled = false;
            stopBtn.disabled = false;
            document.getElementById('player-clear-btn').disabled = false;
        }

        volumeSlider.addEventListener('input', () => { if (currentAudio) currentAudio.volume = volumeSlider.value / 100; });

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
        document.getElementById('player-clear-btn').addEventListener('click', () => {
            stopPlayback();
            currentAudio = null;
            midiData = null;
            playBtn.disabled = true;
            stopBtn.disabled = true;
            document.getElementById('player-clear-btn').disabled = true;
            fileInfo.textContent = 'No file loaded';
        });

        function stopPlayback() {
            isPlaying = false;
            playBtn.textContent = 'Play';
            progress.style.width = '0%';
            currentTimeEl.textContent = '0:00';
            if (currentAudio) { currentAudio.pause(); currentAudio.currentTime = 0; }
            if (midiData) { Tone.Transport.stop(); Tone.Transport.position = 0; synths.forEach(s => s.dispose()); synths = []; }
        }

        async function playMidi() {
            await Tone.start();
            synths.forEach(s => s.dispose());
            synths = [];
            midiData.tracks.forEach(track => {
                const synth = new Tone.PolySynth(Tone.Synth, { envelope: { attack: 0.02, decay: 0.1, sustain: 0.5, release: 0.3 } }).toDestination();
                synth.volume.value = -6;
                synths.push(synth);
                track.notes.forEach(note => {
                    Tone.Transport.schedule(time => synth.triggerAttackRelease(note.name, note.duration, time, note.velocity), note.time);
                });
            });
            Tone.Transport.scheduleRepeat(() => {
                progress.style.width = (Tone.Transport.seconds / midiData.duration * 100) + '%';
                currentTimeEl.textContent = formatTime(Tone.Transport.seconds);
            }, 0.1);
            Tone.Transport.start();
        }

        // ============================================
        // REARRANGE TAB - v3 with original MIDI
        // ============================================
        const pianoRoll = {
            canvas: null,
            ctx: null,
            midiData: null,
            sourceMidiPath: null,
            notes: [],
            tracks: [],
            selectedNote: null,
            isDragging: false,
            dragStartX: 0,
            dragStartY: 0,
            originalNote: null,
            history: [],

            pixelsPerBeat: 40,
            noteHeight: 15,
            minPitch: 24,
            maxPitch: 96,
            scrollX: 0,
            scrollY: 0,
            snap: 0.5,
            tempo: 120,

            isPlaying: false,
            playbackPosition: 0,
            playbackSynths: [],

            trackColors: ['#e94560', '#4ade80', '#60a5fa', '#f59e0b', '#a78bfa', '#ec4899', '#14b8a6', '#f97316'],

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
                    const key = document.createElement('div');
                    key.className = 'piano-key ' + (noteName.includes('#') ? 'black' : 'white');
                    key.textContent = noteName === 'C' ? `C${octave}` : '';
                    key.style.height = this.noteHeight + 'px';
                    keysContainer.appendChild(key);
                }
            },

            setupEventListeners() {
                const dropZone = document.getElementById('rearrange-drop-zone');
                const fileInput = document.getElementById('rearrange-file-input');

                dropZone.addEventListener('click', () => fileInput.click());
                dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
                dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); this.loadFile(e.dataTransfer.files[0]); });
                fileInput.addEventListener('change', e => this.loadFile(e.target.files[0]));

                this.canvas.addEventListener('mousedown', e => this.onMouseDown(e));
                this.canvas.addEventListener('mousemove', e => this.onMouseMove(e));
                this.canvas.addEventListener('mouseup', e => this.onMouseUp(e));
                this.canvas.addEventListener('contextmenu', e => this.onRightClick(e));
                this.canvas.addEventListener('wheel', e => this.onWheel(e));
                document.addEventListener('keydown', e => this.onKeyDown(e));

                document.getElementById('zoom-x').addEventListener('input', e => { this.pixelsPerBeat = parseInt(e.target.value); this.render(); });
                document.getElementById('zoom-y').addEventListener('input', e => { this.noteHeight = parseInt(e.target.value); this.setupPianoKeys(); this.render(); });
                document.getElementById('snap-select').addEventListener('change', e => { this.snap = parseFloat(e.target.value); });
                document.getElementById('undo-btn').addEventListener('click', () => this.undo());
                document.getElementById('clear-btn').addEventListener('click', () => this.clear());
                document.getElementById('export-midi-btn').addEventListener('click', () => this.exportMidi());
                document.getElementById('save-btn').addEventListener('click', () => document.getElementById('save-modal').classList.add('active'));

                document.getElementById('rearrange-play-btn').addEventListener('click', () => this.togglePlayback());
                document.getElementById('rearrange-stop-btn').addEventListener('click', () => this.stopPlayback());

                document.getElementById('save-cancel-btn').addEventListener('click', () => document.getElementById('save-modal').classList.remove('active'));
                document.getElementById('save-confirm-btn').addEventListener('click', () => this.saveAudio());

                document.getElementById('midi-cancel-btn').addEventListener('click', () => document.getElementById('midi-modal').classList.remove('active'));
                document.getElementById('midi-browse-btn').addEventListener('click', () => document.getElementById('midi-file-picker').click());
                document.getElementById('midi-file-picker').addEventListener('change', e => {
                    document.getElementById('midi-modal').classList.remove('active');
                    if (e.target.files[0]) this.loadMidiFile(e.target.files[0]);
                });
            },

            async loadFile(file) {
                if (!file) return;
                const dropZone = document.getElementById('rearrange-drop-zone');
                const isMidi = file.name.endsWith('.mid') || file.name.endsWith('.midi');
                const isAudio = file.name.endsWith('.mp3') || file.name.endsWith('.wav');

                if (isMidi) {
                    this.loadMidiFile(file);
                } else if (isAudio) {
                    // Try to find original MIDI via server
                    dropZone.innerHTML = '<p>Searching for original MIDI...</p>';

                    try {
                        // Just send filename, not the whole file!
                        console.log('Fetching MIDI for:', file.name);
                        const response = await fetch('/api/find-midi?filename=' + encodeURIComponent(file.name));
                        console.log('Response status:', response.status);
                        const result = await response.json();
                        console.log('Result:', result.found, result.midi_path);

                        if (result.found && result.midi_data) {
                            // Server found and sent MIDI data
                            console.log('Decoding base64, length:', result.midi_data.length);
                            // Create proper ArrayBuffer from base64
                            const binaryString = atob(result.midi_data);
                            const buffer = new ArrayBuffer(binaryString.length);
                            const view = new Uint8Array(buffer);
                            for (let i = 0; i < binaryString.length; i++) {
                                view[i] = binaryString.charCodeAt(i);
                            }
                            console.log('MIDI buffer:', buffer.byteLength, 'bytes');
                            const midi = new Midi(buffer);
                            console.log('MIDI parsed, tracks:', midi.tracks.length);
                            this.loadMidiFromTonejs(midi, result.midi_path);
                            this.sourceMidiPath = result.midi_path;
                            document.getElementById('midi-source').textContent = `Source: ${result.midi_path}`;
                        } else {
                            // No MIDI found - show modal
                            dropZone.innerHTML = '<p>Drop MP3/WAV or MIDI file here</p>';
                            document.getElementById('midi-modal-message').textContent =
                                `No MIDI file found for "${file.name}". Please select the MIDI file manually.`;
                            document.getElementById('midi-modal').classList.add('active');
                        }
                    } catch (err) {
                        console.error('Error finding MIDI:', err);
                        console.error('Stack:', err.stack);
                        dropZone.innerHTML = `<p>Error: ${err.message}</p><p style="font-size:0.8rem">Check console (F12)</p>`;
                    }
                }
            },

            async loadMidiFile(file) {
                const arrayBuffer = await file.arrayBuffer();
                const midi = new Midi(arrayBuffer);
                this.loadMidiFromTonejs(midi, file.name);
                this.sourceMidiPath = file.name;
                document.getElementById('midi-source').textContent = `Source: ${file.name}`;
            },

            loadMidiFromTonejs(midi, sourceName) {
                this.midiData = midi;
                this.notes = [];
                this.tracks = [];
                this.tempo = midi.header.tempos[0]?.bpm || 120;

                midi.tracks.forEach((track, trackIndex) => {
                    // Preserve instrument (program) and channel from original MIDI
                    this.tracks.push({
                        index: trackIndex,
                        name: track.name || `Track ${trackIndex + 1}`,
                        color: this.trackColors[trackIndex % this.trackColors.length],
                        visible: true,
                        muted: false,
                        noteCount: track.notes.length,
                        instrument: track.instrument?.number ?? 0,  // GM program number
                        channel: track.channel ?? trackIndex
                    });

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
                dropZone.innerHTML = `<p>Loaded: ${sourceName}</p><p style="font-size:0.8rem;color:#4ade80">${this.notes.length} notes | ${this.tracks.length} tracks | Original MIDI quality!</p>`;

                this.updateTrackList();
                this.updateStatus();
                this.enableButtons();
                this.adjustView();
                this.history = [];
                this.render();
            },

            enableButtons() {
                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = false;
                document.getElementById('export-midi-btn').disabled = false;
                document.getElementById('save-btn').disabled = false;
                document.getElementById('rearrange-play-btn').disabled = false;
                document.getElementById('rearrange-stop-btn').disabled = false;
            },

            adjustView() {
                if (this.notes.length > 0) {
                    const minPitch = Math.min(...this.notes.map(n => n.pitch));
                    const maxPitch = Math.max(...this.notes.map(n => n.pitch));
                    this.minPitch = Math.max(0, minPitch - 5);
                    this.maxPitch = Math.min(127, maxPitch + 5);
                    this.setupPianoKeys();
                }
            },

            updateTrackList() {
                const container = document.getElementById('track-list');
                container.innerHTML = '';
                this.tracks.forEach((track, i) => {
                    const item = document.createElement('div');
                    item.className = 'track-item' + (track.visible ? ' active' : '');
                    const noteCount = this.notes.filter(n => n.trackIndex === i).length;
                    item.innerHTML = `<span class="track-color" style="background:${track.color}"></span><span class="track-name">${track.name}</span><span class="track-notes">${noteCount} notes</span>`;
                    item.addEventListener('click', () => { track.visible = !track.visible; item.classList.toggle('active'); this.render(); });
                    container.appendChild(item);
                });
            },

            updateStatus() {
                document.getElementById('note-count').textContent = `${this.notes.length} notes`;
            },

            saveToHistory() {
                this.history.push(JSON.stringify(this.notes));
                if (this.history.length > 50) this.history.shift();
                document.getElementById('undo-btn').disabled = false;
            },

            undo() {
                if (this.history.length === 0) return;
                this.notes = JSON.parse(this.history.pop());
                this.updateStatus();
                this.updateTrackList();
                this.render();
                document.getElementById('undo-btn').disabled = this.history.length === 0;
            },

            clear() {
                this.stopPlayback();
                this.midiData = null;
                this.sourceMidiPath = null;
                this.notes = [];
                this.tracks = [];
                this.history = [];

                const dropZone = document.getElementById('rearrange-drop-zone');
                dropZone.classList.remove('has-file');
                dropZone.innerHTML = '<p><strong>Drop MP3/WAV or MIDI file here</strong></p><p style="font-size:0.85rem;color:#888;margin-top:8px">MP3/WAV → We find original MIDI automatically</p><input type="file" id="rearrange-file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">';

                const newInput = document.getElementById('rearrange-file-input');
                dropZone.addEventListener('click', () => newInput.click());
                newInput.addEventListener('change', e => this.loadFile(e.target.files[0]));

                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = true;
                document.getElementById('export-midi-btn').disabled = true;
                document.getElementById('save-btn').disabled = true;
                document.getElementById('rearrange-play-btn').disabled = true;
                document.getElementById('rearrange-stop-btn').disabled = true;
                document.getElementById('track-list').innerHTML = '<p style="color:#666;text-align:center;padding:20px;">Load a file to see tracks</p>';
                document.getElementById('note-count').textContent = '0 notes';
                document.getElementById('midi-source').textContent = 'No MIDI loaded';

                this.render();
            },

            render() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                ctx.fillStyle = '#111';
                ctx.fillRect(0, 0, width, height);
                this.drawGrid();

                const visibleTracks = this.tracks.filter(t => t.visible && !t.muted).map(t => t.index);

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

                if (this.playbackPosition > 0) {
                    const px = this.playbackPosition * this.pixelsPerBeat - this.scrollX;
                    ctx.strokeStyle = '#4ade80';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(px, 0);
                    ctx.lineTo(px, height);
                    ctx.stroke();
                }
            },

            drawGrid() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                for (let pitch = this.minPitch; pitch <= this.maxPitch; pitch++) {
                    const y = (this.maxPitch - pitch) * this.noteHeight - this.scrollY;
                    if (y < 0 || y > height) continue;
                    ctx.strokeStyle = pitch % 12 === 0 ? '#333' : '#1a1a1a';
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(width, y);
                    ctx.stroke();
                }

                const maxTime = this.notes.length > 0 ? Math.max(...this.notes.map(n => n.startTime + n.duration)) + 4 : 60;
                for (let beat = 0; beat <= maxTime; beat += 0.25) {
                    const x = beat * this.pixelsPerBeat - this.scrollX;
                    if (x < 0 || x > width) continue;
                    ctx.strokeStyle = beat % 4 === 0 ? '#444' : beat % 1 === 0 ? '#2a2a2a' : '#1a1a1a';
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                }
            },

            getNoteAt(x, y) {
                const visibleTracks = this.tracks.filter(t => t.visible && !t.muted).map(t => t.index);
                for (let i = this.notes.length - 1; i >= 0; i--) {
                    const note = this.notes[i];
                    if (!visibleTracks.includes(note.trackIndex)) continue;
                    const nx = note.startTime * this.pixelsPerBeat - this.scrollX;
                    const ny = (this.maxPitch - note.pitch) * this.noteHeight - this.scrollY;
                    const nw = Math.max(4, note.duration * this.pixelsPerBeat);
                    const nh = this.noteHeight - 2;
                    if (x >= nx && x <= nx + nw && y >= ny && y <= ny + nh) return note;
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
                    document.getElementById('selection-info').textContent = `Selected: ${note.name}`;
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

                if (this.isDragging && this.selectedNote) {
                    const dx = x - this.dragStartX;
                    const dy = y - this.dragStartY;
                    let newTime = this.originalNote.startTime + dx / this.pixelsPerBeat;
                    let newPitch = this.originalNote.pitch - Math.round(dy / this.noteHeight);
                    if (this.snap > 0) newTime = Math.round(newTime / this.snap) * this.snap;
                    newTime = Math.max(0, newTime);
                    newPitch = Math.max(0, Math.min(127, newPitch));
                    this.selectedNote.startTime = newTime;
                    this.selectedNote.pitch = newPitch;
                    const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
                    this.selectedNote.name = noteNames[((newPitch % 12) + 12) % 12] + Math.floor(newPitch / 12 - 1);
                    this.render();
                } else {
                    this.canvas.style.cursor = this.getNoteAt(x, y) ? 'grab' : 'default';
                }
            },

            onMouseUp(e) {
                if (this.isDragging && this.selectedNote) {
                    if (this.selectedNote.startTime !== this.originalNote.startTime || this.selectedNote.pitch !== this.originalNote.pitch) {
                        this.saveToHistory();
                    }
                }
                this.isDragging = false;
                this.canvas.style.cursor = 'default';
            },

            onRightClick(e) {
                e.preventDefault();
                const rect = this.canvas.getBoundingClientRect();
                const note = this.getNoteAt(e.clientX - rect.left, e.clientY - rect.top);
                if (note) this.deleteNote(note);
            },

            onKeyDown(e) {
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    if (this.selectedNote) this.deleteNote(this.selectedNote);
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
                if (e.shiftKey) this.scrollX += e.deltaY;
                else this.scrollY += e.deltaY;
                this.scrollX = Math.max(0, this.scrollX);
                this.scrollY = Math.max(0, this.scrollY);
                this.render();
            },

            deleteNote(note) {
                this.saveToHistory();
                const idx = this.notes.indexOf(note);
                if (idx > -1) {
                    this.notes.splice(idx, 1);
                    this.selectedNote = null;
                    this.updateStatus();
                    this.updateTrackList();
                    document.getElementById('selection-info').textContent = 'Note deleted';
                    this.render();
                }
            },

            async togglePlayback() {
                if (this.isPlaying) this.pausePlayback();
                else await this.startPlayback();
            },

            renderedAudio: null,
            audioElement: null,

            async startPlayback() {
                if (this.notes.length === 0) return;

                this.isPlaying = true;
                document.getElementById('rearrange-play-btn').textContent = 'Rendering...';
                document.getElementById('rearrange-play-btn').disabled = true;

                try {
                    // Build MIDI from current notes WITH instrument programs
                    const newMidi = new Midi();
                    newMidi.header.setTempo(this.tempo);
                    this.tracks.forEach((track, i) => {
                        if (track.muted) return;
                        const t = newMidi.addTrack();
                        t.name = track.name;
                        t.channel = track.channel ?? i;
                        // Set instrument (GM program) - critical for correct sound!
                        t.instrument.number = track.instrument ?? 0;
                        this.notes.filter(n => n.trackIndex === i).forEach(note => {
                            t.addNote({ midi: note.pitch, time: note.startTime, duration: note.duration, velocity: note.velocity / 127 });
                        });
                    });

                    // Send to server for FluidSynth rendering
                    const formData = new FormData();
                    formData.append('midi', new Blob([newMidi.toArray()], { type: 'audio/midi' }), 'arrangement.mid');
                    formData.append('format', 'wav');

                    console.log('Rendering with FluidSynth...');
                    const response = await fetch('/api/render', { method: 'POST', body: formData });

                    if (!response.ok) {
                        throw new Error('Render failed: ' + await response.text());
                    }

                    // Create audio element and play
                    const audioBlob = await response.blob();
                    const audioUrl = URL.createObjectURL(audioBlob);

                    if (this.audioElement) {
                        this.audioElement.pause();
                        URL.revokeObjectURL(this.audioElement.src);
                    }

                    this.audioElement = new Audio(audioUrl);
                    this.audioElement.volume = 0.8;

                    const maxTime = this.notes.length > 0 ? Math.max(...this.notes.map(n => n.startTime + n.duration)) : 10;

                    this.audioElement.addEventListener('timeupdate', () => {
                        this.playbackPosition = this.audioElement.currentTime;
                        document.getElementById('rearrange-time').textContent = `${formatTime(this.playbackPosition)} / ${formatTime(maxTime)}`;
                        this.render();
                    });

                    this.audioElement.addEventListener('ended', () => {
                        this.stopPlayback();
                    });

                    document.getElementById('rearrange-play-btn').textContent = 'Pause';
                    document.getElementById('rearrange-play-btn').disabled = false;
                    await this.audioElement.play();
                    console.log('Playing with production quality!');

                } catch (err) {
                    console.error('Playback error:', err);
                    document.getElementById('rearrange-play-btn').textContent = 'Play';
                    document.getElementById('rearrange-play-btn').disabled = false;
                    this.isPlaying = false;
                    alert('Rendering failed: ' + err.message);
                }
            },

            pausePlayback() {
                this.isPlaying = false;
                document.getElementById('rearrange-play-btn').textContent = 'Play';
                if (this.audioElement) {
                    this.audioElement.pause();
                }
            },

            stopPlayback() {
                this.isPlaying = false;
                this.playbackPosition = 0;
                document.getElementById('rearrange-play-btn').textContent = 'Play';
                document.getElementById('rearrange-time').textContent = '0:00 / 0:00';
                if (this.audioElement) {
                    this.audioElement.pause();
                    this.audioElement.currentTime = 0;
                }
                this.render();
            },

            exportMidi() {
                if (this.notes.length === 0) return;
                const newMidi = new Midi();
                newMidi.header.setTempo(this.tempo);
                this.tracks.forEach((track, i) => {
                    const t = newMidi.addTrack();
                    t.name = track.name;
                    t.channel = track.channel ?? i;
                    t.instrument.number = track.instrument ?? 0;
                    this.notes.filter(n => n.trackIndex === i).forEach(note => {
                        t.addNote({ midi: note.pitch, time: note.startTime, duration: note.duration, velocity: note.velocity / 127 });
                    });
                });
                const blob = new Blob([newMidi.toArray()], { type: 'audio/midi' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'rearranged.mid';
                a.click();
            },

            async saveAudio() {
                const format = document.querySelector('input[name="format"]:checked').value;
                const status = document.getElementById('save-status');
                status.textContent = 'Rendering...';

                try {
                    const newMidi = new Midi();
                    newMidi.header.setTempo(this.tempo);
                    this.tracks.forEach((track, i) => {
                        const t = newMidi.addTrack();
                        t.name = track.name;
                        t.channel = track.channel ?? i;
                        t.instrument.number = track.instrument ?? 0;
                        this.notes.filter(n => n.trackIndex === i).forEach(note => {
                            t.addNote({ midi: note.pitch, time: note.startTime, duration: note.duration, velocity: note.velocity / 127 });
                        });
                    });

                    const formData = new FormData();
                    formData.append('midi', new Blob([newMidi.toArray()], { type: 'audio/midi' }), 'arrangement.mid');
                    formData.append('format', format);

                    const response = await fetch('/api/render', { method: 'POST', body: formData });
                    if (!response.ok) throw new Error(await response.text());

                    const blob = await response.blob();
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = `rearranged.${format}`;
                    a.click();

                    status.textContent = 'Saved!';
                    setTimeout(() => document.getElementById('save-modal').classList.remove('active'), 1000);
                } catch (err) {
                    status.textContent = 'Error: ' + err.message;
                }
            }
        };

        pianoRoll.init();
    </script>
</body>
</html>
"""


class PlayerHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with API for MIDI finding and rendering."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/player.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(BROWSER_PLAYER_V3_HTML.encode())
        elif parsed.path == '/api/find-midi':
            self.handle_find_midi_get(parsed.query)
        else:
            self.send_error(404)

    def handle_find_midi_get(self, query_string):
        """Find original MIDI file - GET version with filename in query."""
        import base64
        import sys
        from urllib.parse import parse_qs
        try:
            params = parse_qs(query_string)
            filename = params.get('filename', ['audio.mp3'])[0]
            print(f"[find-midi] Looking for MIDI for: {filename}", flush=True)

            # Use fixed arrangement MIDI with all 7 tracks
            # Use latest pipeline output (matching production quality, gain=1.5)
            midi_path = Path("C:/Users/haege/Kod/Music/output_2026-02-26_1034/02_arrangement.mid")
            if not midi_path.exists():
                midi_path = Path("C:/Users/haege/Kod/Music/output_2026-02-26_0946/02_arrangement.mid")
            if not midi_path.exists():
                midi_path = Path("C:/Users/haege/Kod/Music/output_new/01_melody.mid")

            if midi_path.exists():
                print(f"[find-midi] Found: {midi_path}", flush=True)
                with open(midi_path, 'rb') as f:
                    midi_data = f.read()
                print(f"[find-midi] Read {len(midi_data)} bytes", flush=True)

                encoded = base64.b64encode(midi_data).decode('ascii')
                print(f"[find-midi] Encoded to {len(encoded)} chars", flush=True)

                result = {
                    "found": True,
                    "midi_path": str(midi_path.name),
                    "midi_data": encoded
                }
            else:
                print(f"[find-midi] Not found", flush=True)
                result = {"found": False, "midi_path": None}

            response_data = json.dumps(result).encode()
            print(f"[find-midi] Sending {len(response_data)} bytes response", flush=True)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_data)
            self.wfile.flush()
            print(f"[find-midi] Response sent OK", flush=True)

        except Exception as e:
            import traceback
            print(f"[find-midi] ERROR: {e}", flush=True)
            traceback.print_exc()
            error_response = json.dumps({"found": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response)
            self.wfile.flush()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/find-midi':
            self.handle_find_midi()
        elif parsed.path == '/api/render':
            self.handle_render()
        else:
            self.send_error(404)

    def handle_find_midi(self):
        """Find original MIDI file for audio."""
        import base64
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))

            print(f"[find-midi] Content-Type: {content_type}, Length: {content_length}")

            # Read body
            body = self.rfile.read(content_length) if content_length > 0 else b''

            # Parse filename from multipart (if present)
            filename = 'audio.mp3'
            if 'boundary=' in content_type:
                try:
                    boundary = content_type.split('boundary=')[1].encode()
                    parts = body.split(b'--' + boundary)
                    for part in parts:
                        if b'filename=' in part:
                            header = part.split(b'\r\n\r\n')[0].decode('utf-8', errors='ignore')
                            for line in header.split('\r\n'):
                                if 'filename=' in line:
                                    filename = line.split('filename=')[1].strip('"\'')
                                    break
                except Exception as parse_err:
                    print(f"[find-midi] Parse error: {parse_err}")

            print(f"[find-midi] Looking for MIDI for: {filename}")

            # Use latest pipeline output (matching production quality, gain=1.5)
            midi_path = Path("C:/Users/haege/Kod/Music/output_2026-02-26_1034/02_arrangement.mid")
            if not midi_path.exists():
                midi_path = Path("C:/Users/haege/Kod/Music/output_2026-02-26_0946/02_arrangement.mid")
            if not midi_path.exists():
                midi_path = Path("C:/Users/haege/Kod/Music/output_new/01_melody.mid")

            if midi_path.exists():
                print(f"[find-midi] Found: {midi_path}")
                with open(midi_path, 'rb') as f:
                    midi_data = f.read()

                result = {
                    "found": True,
                    "midi_path": str(midi_path.name),
                    "midi_data": base64.b64encode(midi_data).decode('ascii')
                }
            else:
                print(f"[find-midi] No MIDI found")
                result = {"found": False, "midi_path": None}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            print(f"[find-midi] Response sent: found={result['found']}")

        except Exception as e:
            print(f"[find-midi] ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"found": False, "error": str(e)}).encode())

    def handle_render(self):
        """Render MIDI to audio."""
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

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

            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
                f.write(midi_data)
                midi_path = f.name

            output_path = tempfile.mktemp(suffix=f'.{output_format}')

            try:
                if midi_to_audio(midi_path, output_path, output_format):
                    with open(output_path, 'rb') as f:
                        audio_data = f.read()

                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/wav' if output_format == 'wav' else 'audio/mpeg')
                    self.end_headers()
                    self.wfile.write(audio_data)
                else:
                    self.send_error(500, 'FluidSynth not available')
            finally:
                if os.path.exists(midi_path):
                    os.unlink(midi_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            print(f"Render error: {e}")
            self.send_error(500, str(e))


def serve_player_v3(port: int = 8765) -> threading.Thread:
    """Start player server."""
    def serve():
        with socketserver.TCPServer(("", port), PlayerHandler) as httpd:
            print(f"Server running on http://localhost:{port}")
            httpd.serve_forever()
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread


def play_with_rearrange_v3(port: int = 8765) -> PlaybackResult:
    """Open browser player with Rearrange v3."""
    serve_player_v3(port)
    url = f"http://localhost:{port}/player.html"
    webbrowser.open(url)
    return PlaybackResult(success=True, method=PlaybackMethod.BROWSER, message=f"Rearrange v3 at {url}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(line_buffering=True)  # Unbuffered output

    print("Starting Rearrange Player v3...")
    print("NEW in v3: Uses original MIDI files for perfect quality!")
    print()

    PORT = 8765

    # Use ThreadingTCPServer for concurrent request handling
    class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    print(f"Starting server on http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")

    with ThreadingServer(("", PORT), PlayerHandler) as httpd:
        print("Server ready! Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
