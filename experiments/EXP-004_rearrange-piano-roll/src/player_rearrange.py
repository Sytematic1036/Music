"""
Extended player module with Rearrange (Piano Roll) tab.

Adds to the existing player.py:
- Rearrange tab with canvas-based piano roll
- Drag notes to change timing (horizontal)
- Drag notes to change pitch (vertical)
- Delete notes with right-click or Delete key
- Export modified MIDI

This module is designed to be integrated into the existing player.py
by replacing BROWSER_PLAYER_HTML with BROWSER_PLAYER_WITH_REARRANGE_HTML.
"""

import json
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import http.server
import socketserver
import webbrowser


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


# Extended HTML template with Rearrange tab
BROWSER_PLAYER_WITH_REARRANGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Player - EXP-004 Rearrange</title>
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
            max-width: 1200px;
        }
        .tab-content.active {
            display: block;
        }

        /* Player Panel (existing) */
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
        /* REARRANGE TAB - Piano Roll Styles           */
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
            cursor: default;
        }

        .piano-roll-container {
            position: relative;
            background: #111;
            border-radius: 10px;
            overflow: hidden;
        }

        /* Piano keys on left side */
        .piano-keys {
            position: absolute;
            left: 0;
            top: 0;
            width: 60px;
            height: 100%;
            background: #222;
            border-right: 1px solid #333;
            z-index: 10;
        }

        .piano-key {
            height: 20px;
            border-bottom: 1px solid #333;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 5px;
            font-size: 10px;
            color: #666;
        }
        .piano-key.black {
            background: #1a1a1a;
        }
        .piano-key.white {
            background: #2a2a2a;
        }

        /* Canvas area */
        #piano-roll-canvas {
            display: block;
            margin-left: 60px;
            cursor: default;
        }

        /* Note styles are rendered on canvas, but we define colors here for reference */
        .note-info {
            position: fixed;
            background: rgba(0,0,0,0.8);
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 12px;
            pointer-events: none;
            display: none;
            z-index: 100;
        }

        /* Track list */
        .track-list {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .track-item {
            background: rgba(255,255,255,0.1);
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .track-item:hover {
            background: rgba(255,255,255,0.2);
        }
        .track-item.active {
            background: rgba(233,69,96,0.3);
            border: 1px solid #e94560;
        }
        .track-item .track-color {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 3px;
            margin-right: 8px;
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
    </style>
</head>
<body>
    <!-- Tab Navigation -->
    <div class="tabs">
        <button class="tab active" data-tab="player">Player</button>
        <button class="tab" data-tab="rearrange">Rearrange</button>
    </div>

    <!-- Player Tab (Original) -->
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

    <!-- Rearrange Tab (New) -->
    <div class="tab-content" id="tab-rearrange">
        <div class="rearrange-panel">
            <h2>Piano Roll Editor</h2>

            <div id="rearrange-drop-zone">
                <p>Drop MIDI file here to edit</p>
                <p style="font-size: 0.85rem; color: #888; margin-top: 8px">or click to browse files</p>
                <input type="file" id="rearrange-file-input" accept=".mid,.midi" style="display:none">
            </div>

            <div class="rearrange-toolbar">
                <div class="toolbar-group">
                    <span class="toolbar-label">Zoom:</span>
                    <input type="range" id="zoom-x" min="10" max="100" value="40" title="Horizontal zoom">
                    <input type="range" id="zoom-y" min="10" max="40" value="20" title="Vertical zoom">
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
                    <button id="export-btn" disabled>Export MIDI</button>
                </div>
            </div>

            <div class="piano-roll-container">
                <div class="piano-keys" id="piano-keys"></div>
                <canvas id="piano-roll-canvas" width="1000" height="600"></canvas>
            </div>

            <div class="track-list" id="track-list">
                <!-- Tracks will be added dynamically -->
            </div>

            <div class="status-bar">
                <span id="note-count">0 notes</span>
                <span id="selection-info">No selection</span>
                <span id="cursor-info">-</span>
            </div>

            <div class="help-text">
                <strong>Controls:</strong>
                Drag note horizontally = change time |
                Drag note vertically = change pitch |
                <kbd>Delete</kbd> or Right-click = remove note |
                <kbd>Ctrl+Z</kbd> = undo |
                Mouse wheel = scroll
            </div>
        </div>
    </div>

    <div class="note-info" id="note-info"></div>

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

            // Reset UI
            playBtn.disabled = true;
            stopBtn.disabled = true;
            playerClearBtn.disabled = true;
            totalTimeEl.textContent = '0:00';
            fileInfo.textContent = 'No file loaded';

            // Reset drop zone
            dropZone.innerHTML = `
                <p>Drop MIDI/WAV/MP3 file here</p>
                <p style="font-size: 0.8rem; color: #666; margin-top: 10px">or click to select</p>
                <input type="file" id="file-input" accept=".mid,.midi,.wav,.mp3" style="display:none">
            `;

            // Re-attach file input listener
            const newFileInput = document.getElementById('file-input');
            dropZone.addEventListener('click', () => newFileInput.click());
            newFileInput.addEventListener('change', (e) => handlePlayerFile(e.target.files[0]));

            // Reset stages
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
        // REARRANGE TAB - Piano Roll
        // ============================================
        const pianoRoll = {
            canvas: null,
            ctx: null,
            midiData: null,
            notes: [],  // Flat array of all notes for editing
            tracks: [], // Track metadata
            selectedNote: null,
            isDragging: false,
            dragStartX: 0,
            dragStartY: 0,
            originalNote: null,
            history: [],
            maxHistory: 50,

            // Display settings
            pixelsPerBeat: 40,
            noteHeight: 20,
            minPitch: 36,  // C2
            maxPitch: 96,  // C7
            scrollX: 0,
            scrollY: 0,
            snap: 0.5,

            // Track colors
            trackColors: [
                '#e94560', // Red
                '#4ade80', // Green
                '#60a5fa', // Blue
                '#f59e0b', // Orange
                '#a78bfa', // Purple
                '#ec4899', // Pink
                '#14b8a6', // Teal
                '#f97316', // Dark orange
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
                    key.dataset.pitch = pitch;
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
                document.getElementById('export-btn').addEventListener('click', () => this.exportMidi());
            },

            async loadFile(file) {
                if (!file || (!file.name.endsWith('.mid') && !file.name.endsWith('.midi'))) {
                    alert('Please select a MIDI file');
                    return;
                }

                const arrayBuffer = await file.arrayBuffer();
                this.midiData = new Midi(arrayBuffer);
                this.notes = [];
                this.tracks = [];

                // Convert MIDI data to editable notes
                this.midiData.tracks.forEach((track, trackIndex) => {
                    const trackInfo = {
                        index: trackIndex,
                        name: track.name || `Track ${trackIndex + 1}`,
                        color: this.trackColors[trackIndex % this.trackColors.length],
                        visible: true,
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

                // Update UI
                const dropZone = document.getElementById('rearrange-drop-zone');
                dropZone.classList.add('has-file');
                dropZone.innerHTML = `<p>Loaded: ${file.name}</p><p style="font-size: 0.8rem; color: #4ade80">${this.notes.length} notes in ${this.tracks.length} tracks</p>`;

                this.updateTrackList();
                this.updateStatus();
                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = false;
                document.getElementById('export-btn').disabled = false;

                // Adjust view
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
                    item.className = 'track-item' + (track.visible ? ' active' : '');
                    item.innerHTML = `<span class="track-color" style="background: ${track.color}"></span>${track.name} (${track.noteCount})`;
                    item.addEventListener('click', () => {
                        track.visible = !track.visible;
                        item.classList.toggle('active');
                        this.render();
                    });
                    container.appendChild(item);
                });
            },

            updateStatus() {
                document.getElementById('note-count').textContent = `${this.notes.length} notes`;
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
                // Reset all data
                this.midiData = null;
                this.notes = [];
                this.tracks = [];
                this.selectedNote = null;
                this.history = [];

                // Reset drop zone
                const dropZone = document.getElementById('rearrange-drop-zone');
                dropZone.classList.remove('has-file');
                dropZone.innerHTML = `
                    <p>Drop MIDI file here to edit</p>
                    <p style="font-size: 0.85rem; color: #888; margin-top: 8px">or click to browse files</p>
                    <input type="file" id="rearrange-file-input" accept=".mid,.midi" style="display:none">
                `;

                // Re-attach file input listener
                const fileInput = document.getElementById('rearrange-file-input');
                dropZone.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', (e) => this.loadFile(e.target.files[0]));

                // Reset buttons
                document.getElementById('undo-btn').disabled = true;
                document.getElementById('clear-btn').disabled = true;
                document.getElementById('export-btn').disabled = true;

                // Reset track list
                document.getElementById('track-list').innerHTML = '';

                // Reset status
                document.getElementById('note-count').textContent = '0 notes';
                document.getElementById('selection-info').textContent = 'No selection';

                // Re-render empty canvas
                this.render();
            },

            render() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                // Clear
                ctx.fillStyle = '#111';
                ctx.fillRect(0, 0, width, height);

                // Draw grid
                this.drawGrid();

                // Draw notes
                const visibleTracks = this.tracks.filter(t => t.visible).map(t => t.index);

                this.notes.forEach(note => {
                    if (!visibleTracks.includes(note.trackIndex)) return;

                    const x = note.startTime * this.pixelsPerBeat - this.scrollX;
                    const y = (this.maxPitch - note.pitch) * this.noteHeight - this.scrollY;
                    const w = note.duration * this.pixelsPerBeat;
                    const h = this.noteHeight - 2;

                    // Skip if outside viewport
                    if (x + w < 0 || x > width || y + h < 0 || y > height) return;

                    // Note rectangle
                    const track = this.tracks[note.trackIndex];
                    ctx.fillStyle = note === this.selectedNote ? '#fff' : track.color;
                    ctx.fillRect(x, y, w, h);

                    // Note border
                    ctx.strokeStyle = note === this.selectedNote ? '#e94560' : 'rgba(0,0,0,0.5)';
                    ctx.lineWidth = note === this.selectedNote ? 2 : 1;
                    ctx.strokeRect(x, y, w, h);

                    // Note name (if wide enough)
                    if (w > 30) {
                        ctx.fillStyle = note === this.selectedNote ? '#000' : '#fff';
                        ctx.font = '10px sans-serif';
                        ctx.fillText(note.name || '', x + 3, y + h - 4);
                    }
                });

                // Draw playhead position indicator if needed
            },

            drawGrid() {
                const ctx = this.ctx;
                const width = this.canvas.width;
                const height = this.canvas.height;

                // Horizontal lines (pitch)
                ctx.strokeStyle = '#222';
                ctx.lineWidth = 1;

                for (let pitch = this.minPitch; pitch <= this.maxPitch; pitch++) {
                    const y = (this.maxPitch - pitch) * this.noteHeight - this.scrollY;
                    if (y < 0 || y > height) continue;

                    // Highlight C notes
                    if (pitch % 12 === 0) {
                        ctx.strokeStyle = '#333';
                    } else {
                        ctx.strokeStyle = '#1a1a1a';
                    }

                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(width, y);
                    ctx.stroke();
                }

                // Vertical lines (beats)
                const maxTime = this.midiData ? this.midiData.duration : 60;

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
                const visibleTracks = this.tracks.filter(t => t.visible).map(t => t.index);

                // Check in reverse order (top notes first)
                for (let i = this.notes.length - 1; i >= 0; i--) {
                    const note = this.notes[i];
                    if (!visibleTracks.includes(note.trackIndex)) continue;

                    const nx = note.startTime * this.pixelsPerBeat - this.scrollX;
                    const ny = (this.maxPitch - note.pitch) * this.noteHeight - this.scrollY;
                    const nw = note.duration * this.pixelsPerBeat;
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

                // Update cursor info
                const beat = (x + this.scrollX) / this.pixelsPerBeat;
                const pitch = Math.round(this.maxPitch - (y + this.scrollY) / this.noteHeight);
                const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
                const noteName = noteNames[pitch % 12] + Math.floor(pitch / 12 - 1);
                document.getElementById('cursor-info').textContent = `Beat: ${beat.toFixed(2)} | ${noteName}`;

                if (this.isDragging && this.selectedNote) {
                    const dx = x - this.dragStartX;
                    const dy = y - this.dragStartY;

                    // Calculate new position
                    let newTime = this.originalNote.startTime + dx / this.pixelsPerBeat;
                    let newPitch = this.originalNote.pitch - Math.round(dy / this.noteHeight);

                    // Apply snap
                    if (this.snap > 0) {
                        newTime = Math.round(newTime / this.snap) * this.snap;
                    }

                    // Clamp
                    newTime = Math.max(0, newTime);
                    newPitch = Math.max(0, Math.min(127, newPitch));

                    this.selectedNote.startTime = newTime;
                    this.selectedNote.pitch = newPitch;
                    this.selectedNote.name = noteNames[newPitch % 12] + Math.floor(newPitch / 12 - 1);

                    document.getElementById('selection-info').textContent =
                        `Moving: ${this.selectedNote.name} (t=${newTime.toFixed(2)})`;

                    this.render();
                } else {
                    // Hover cursor
                    const note = this.getNoteAt(x, y);
                    this.canvas.style.cursor = note ? 'grab' : 'default';
                }
            },

            onMouseUp(e) {
                if (this.isDragging && this.selectedNote) {
                    // Check if position actually changed
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
                }
            },

            onWheel(e) {
                e.preventDefault();

                if (e.shiftKey) {
                    // Horizontal scroll
                    this.scrollX += e.deltaY;
                } else {
                    // Vertical scroll
                    this.scrollY += e.deltaY;
                }

                // Clamp
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
                    document.getElementById('selection-info').textContent = 'Note deleted';
                    this.render();
                }
            },

            exportMidi() {
                if (!this.midiData) return;

                // Create new MIDI with edited notes
                const newMidi = new Midi();
                newMidi.header = this.midiData.header;

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

                // Download
                const blob = new Blob([newMidi.toArray()], { type: 'audio/midi' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'rearranged.mid';
                a.click();
                URL.revokeObjectURL(url);
            }
        };

        // Initialize piano roll when page loads
        pianoRoll.init();
    </script>
</body>
</html>
"""


def create_browser_player_with_rearrange(
    output_dir: str | Path,
) -> str:
    """
    Create browser-based player HTML with Rearrange tab.

    Args:
        output_dir: Directory to save player

    Returns:
        Path to player HTML file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    player_path = output_dir / "player.html"
    with open(player_path, "w", encoding="utf-8") as f:
        f.write(BROWSER_PLAYER_WITH_REARRANGE_HTML)

    return str(player_path)


def serve_browser_player(
    player_path: str | Path,
    port: int = 8765
) -> threading.Thread:
    """
    Serve browser player on local HTTP server.

    Args:
        player_path: Path to player HTML
        port: Port to serve on

    Returns:
        Server thread
    """
    player_path = Path(player_path)
    directory = player_path.parent

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress logging

    def serve():
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    return thread


def play_with_rearrange(
    file_path: str | Path = None,
    port: int = 8765
) -> PlaybackResult:
    """
    Open browser player with Rearrange tab.

    Args:
        file_path: Optional MIDI file to load
        port: HTTP server port

    Returns:
        PlaybackResult
    """
    import tempfile

    # Create player in temp directory
    player_dir = Path(tempfile.mkdtemp())
    player_path = create_browser_player_with_rearrange(player_dir)

    # Start server
    serve_browser_player(player_path, port)

    # Open browser
    url = f"http://localhost:{port}/player.html"
    webbrowser.open(url)

    return PlaybackResult(
        success=True,
        method=PlaybackMethod.BROWSER,
        message=f"Rearrange player opened at {url}",
        file_path=player_path
    )


if __name__ == "__main__":
    import sys

    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    print("Starting Rearrange Player...")
    result = play_with_rearrange(file_path)
    print(f"Result: {result.message}")

    # Keep server running
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped.")
