"""
Player module for MIDI and audio playback.

Three playback methods:
1. Browser - HTML/JS Web MIDI/Audio player
2. Python - pygame/fluidsynth direct playback
3. Export - Render to WAV/MP3 for external playback
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

from .production import (
    find_soundfont,
    download_soundfont,
    check_fluidsynth,
    check_ffmpeg,
    midi_to_wav,
    wav_to_mp3,
    MixSettings,
    GENRE_MIX_PRESETS,
    ProductionPreset
)


class PlaybackMethod(Enum):
    """Available playback methods."""
    BROWSER = "browser"    # Web-based player
    PYTHON = "python"      # pygame/fluidsynth
    EXPORT = "export"      # Render to file


@dataclass
class PlaybackResult:
    """Result of playback operation."""
    success: bool
    method: PlaybackMethod
    message: str = ""
    file_path: Optional[str] = None


def check_pygame() -> bool:
    """Check if pygame is available."""
    try:
        import pygame
        return True
    except ImportError:
        return False


# HTML template for browser-based MIDI player
BROWSER_PLAYER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Player - EXP-003</title>
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
            justify-content: center;
            align-items: center;
        }
        .player {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        h1 {
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
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1rem;
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
    </style>
</head>
<body>
    <div class="player">
        <h1>🎵 Music Pipeline Player</h1>

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
            <p>🎹 Drop MIDI/WAV/MP3 file here</p>
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
            <button id="play-btn" disabled>▶ Play</button>
            <button id="stop-btn" disabled>⏹ Stop</button>
        </div>

        <div class="volume-control">
            <span>🔈</span>
            <input type="range" id="volume" min="0" max="100" value="80">
            <span>🔊</span>
        </div>

        <div class="file-info" id="file-info">
            No file loaded
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/tone@14/build/Tone.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@tonejs/midi@2/dist/Midi.min.js"></script>
    <script>
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

        // Stage highlighting
        function setActiveStage(stage) {
            document.querySelectorAll('.stage').forEach(s => s.classList.remove('active'));
            if (stage) {
                document.getElementById('stage-' + stage).classList.add('active');
            }
        }

        // Format time
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins + ':' + secs.toString().padStart(2, '0');
        }

        // Drag and drop
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

        // Handle file
        async function handleFile(file) {
            if (!file) return;

            stop();
            fileInfo.textContent = 'Loading: ' + file.name;

            // Determine stage from filename
            if (file.name.includes('melody')) setActiveStage('melody');
            else if (file.name.includes('arrangement')) setActiveStage('arrangement');
            else if (file.name.includes('production')) setActiveStage('production');

            if (file.name.endsWith('.mid') || file.name.endsWith('.midi')) {
                // MIDI file
                const arrayBuffer = await file.arrayBuffer();
                midiData = new Midi(arrayBuffer);
                currentAudio = null;
                totalTimeEl.textContent = formatTime(midiData.duration);
                fileInfo.textContent = `MIDI: ${file.name} | ${midiData.tracks.length} tracks | ${formatTime(midiData.duration)}`;
            } else {
                // Audio file (WAV/MP3)
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
                    playBtn.textContent = '▶ Play';
                });
            }

            playBtn.disabled = false;
            stopBtn.disabled = false;
        }

        // Volume control
        volumeSlider.addEventListener('input', () => {
            if (currentAudio) {
                currentAudio.volume = volumeSlider.value / 100;
            }
        });

        // Play
        playBtn.addEventListener('click', async () => {
            if (isPlaying) {
                // Pause
                if (currentAudio) {
                    currentAudio.pause();
                } else if (midiData) {
                    Tone.Transport.pause();
                }
                isPlaying = false;
                playBtn.textContent = '▶ Play';
            } else {
                // Play
                if (currentAudio) {
                    currentAudio.play();
                } else if (midiData) {
                    await playMidi();
                }
                isPlaying = true;
                playBtn.textContent = '⏸ Pause';
            }
        });

        // Stop
        stopBtn.addEventListener('click', stop);

        function stop() {
            isPlaying = false;
            playBtn.textContent = '▶ Play';
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

        // Play MIDI using Tone.js
        async function playMidi() {
            await Tone.start();

            // Create synths for each track
            synths.forEach(s => s.dispose());
            synths = [];

            midiData.tracks.forEach((track, i) => {
                const synth = new Tone.PolySynth(Tone.Synth, {
                    envelope: {
                        attack: 0.02,
                        decay: 0.1,
                        sustain: 0.5,
                        release: 0.3
                    }
                }).toDestination();

                synth.volume.value = -6;
                synths.push(synth);

                track.notes.forEach(note => {
                    Tone.Transport.schedule((time) => {
                        synth.triggerAttackRelease(
                            note.name,
                            note.duration,
                            time,
                            note.velocity
                        );
                    }, note.time);
                });
            });

            // Progress updates
            Tone.Transport.scheduleRepeat((time) => {
                const pos = Tone.Transport.seconds;
                const pct = (pos / midiData.duration) * 100;
                progress.style.width = pct + '%';
                currentTimeEl.textContent = formatTime(pos);
            }, 0.1);

            Tone.Transport.start();
        }
    </script>
</body>
</html>
"""


def create_browser_player(
    output_dir: str | Path,
    midi_files: Optional[list[str]] = None,
    audio_files: Optional[list[str]] = None
) -> str:
    """
    Create browser-based player HTML.

    Args:
        output_dir: Directory to save player
        midi_files: Optional list of MIDI files to embed
        audio_files: Optional list of audio files

    Returns:
        Path to player HTML file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    player_path = output_dir / "player.html"
    with open(player_path, "w", encoding="utf-8") as f:
        f.write(BROWSER_PLAYER_HTML)

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


def play_with_browser(
    file_path: str | Path,
    port: int = 8765
) -> PlaybackResult:
    """
    Play file using browser player.

    Args:
        file_path: MIDI or audio file to play
        port: HTTP server port

    Returns:
        PlaybackResult
    """
    file_path = Path(file_path)

    # Create player in same directory as file
    player_dir = file_path.parent
    player_path = create_browser_player(player_dir)

    # Start server
    serve_browser_player(player_path, port)

    # Open browser
    url = f"http://localhost:{port}/player.html"
    webbrowser.open(url)

    return PlaybackResult(
        success=True,
        method=PlaybackMethod.BROWSER,
        message=f"Browser player opened at {url}. Drag and drop your file to play.",
        file_path=player_path
    )


def play_with_python(
    file_path: str | Path,
    volume: float = 0.8,
    wait: bool = False
) -> PlaybackResult:
    """
    Play audio file using pygame.

    Args:
        file_path: WAV or MP3 file to play
        volume: Volume level (0-1)
        wait: Whether to block until playback finishes

    Returns:
        PlaybackResult
    """
    file_path = Path(file_path)

    # For MIDI files, render to WAV first
    if file_path.suffix.lower() in [".mid", ".midi"]:
        soundfont = find_soundfont() or download_soundfont()
        if not soundfont:
            return PlaybackResult(
                success=False,
                method=PlaybackMethod.PYTHON,
                message="No SoundFont available for MIDI playback"
            )

        # Render to temp WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        if not midi_to_wav(file_path, wav_path, soundfont):
            return PlaybackResult(
                success=False,
                method=PlaybackMethod.PYTHON,
                message="Failed to render MIDI to WAV"
            )
        file_path = Path(wav_path)

    # Try pygame first
    if check_pygame():
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()

            if wait:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

            return PlaybackResult(
                success=True,
                method=PlaybackMethod.PYTHON,
                message=f"Playing: {file_path.name}",
                file_path=str(file_path)
            )
        except Exception as e:
            return PlaybackResult(
                success=False,
                method=PlaybackMethod.PYTHON,
                message=f"pygame error: {e}"
            )

    # Fallback to system player
    try:
        if Path(file_path).suffix.lower() == ".wav":
            import winsound
            winsound.PlaySound(str(file_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return PlaybackResult(
                success=True,
                method=PlaybackMethod.PYTHON,
                message=f"Playing with system: {file_path.name}",
                file_path=str(file_path)
            )
    except Exception:
        pass

    return PlaybackResult(
        success=False,
        method=PlaybackMethod.PYTHON,
        message="No audio playback available. Install pygame: pip install pygame"
    )


def play_with_fluidsynth(
    midi_path: str | Path,
    soundfont_path: Optional[str] = None,
    wait: bool = True
) -> PlaybackResult:
    """
    Play MIDI directly with FluidSynth.

    Args:
        midi_path: Path to MIDI file
        soundfont_path: Path to SoundFont
        wait: Whether to block until done

    Returns:
        PlaybackResult
    """
    if not check_fluidsynth():
        return PlaybackResult(
            success=False,
            method=PlaybackMethod.PYTHON,
            message="FluidSynth not installed"
        )

    soundfont = soundfont_path or find_soundfont() or download_soundfont()
    if not soundfont:
        return PlaybackResult(
            success=False,
            method=PlaybackMethod.PYTHON,
            message="No SoundFont available"
        )

    cmd = [
        "fluidsynth",
        "-a", "dsound" if subprocess.sys.platform == "win32" else "pulseaudio",
        "-g", "1.0",
        soundfont,
        str(midi_path)
    ]

    try:
        if wait:
            subprocess.run(cmd, timeout=300)
        else:
            subprocess.Popen(cmd)

        return PlaybackResult(
            success=True,
            method=PlaybackMethod.PYTHON,
            message=f"Playing with FluidSynth: {Path(midi_path).name}",
            file_path=str(midi_path)
        )
    except Exception as e:
        return PlaybackResult(
            success=False,
            method=PlaybackMethod.PYTHON,
            message=f"FluidSynth error: {e}"
        )


def export_for_playback(
    midi_path: str | Path,
    output_dir: str | Path,
    preset: ProductionPreset = ProductionPreset.RELAXATION,
    export_wav: bool = True,
    export_mp3: bool = True
) -> PlaybackResult:
    """
    Export MIDI to audio files for external playback.

    Args:
        midi_path: Path to MIDI file
        output_dir: Directory for output
        preset: Production preset to use
        export_wav: Export WAV
        export_mp3: Export MP3

    Returns:
        PlaybackResult with file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    soundfont = find_soundfont() or download_soundfont()
    if not soundfont:
        return PlaybackResult(
            success=False,
            method=PlaybackMethod.EXPORT,
            message="No SoundFont available"
        )

    # Render WAV
    wav_path = output_dir / f"{Path(midi_path).stem}.wav"
    if not midi_to_wav(midi_path, wav_path, soundfont):
        return PlaybackResult(
            success=False,
            method=PlaybackMethod.EXPORT,
            message="Failed to render WAV"
        )

    result_path = str(wav_path)

    # Export MP3
    if export_mp3:
        mp3_path = output_dir / f"{Path(midi_path).stem}.mp3"
        if wav_to_mp3(wav_path, mp3_path):
            result_path = str(mp3_path)

    return PlaybackResult(
        success=True,
        method=PlaybackMethod.EXPORT,
        message=f"Exported: {result_path}",
        file_path=result_path
    )


def play(
    file_path: str | Path,
    method: Optional[PlaybackMethod] = None,
    **kwargs
) -> PlaybackResult:
    """
    Universal play function - automatically selects best method.

    Args:
        file_path: Path to MIDI or audio file
        method: Force specific method, or None for auto

    Returns:
        PlaybackResult
    """
    file_path = Path(file_path)

    if method == PlaybackMethod.BROWSER:
        return play_with_browser(file_path, **kwargs)
    elif method == PlaybackMethod.PYTHON:
        if file_path.suffix.lower() in [".mid", ".midi"]:
            return play_with_fluidsynth(file_path, **kwargs)
        return play_with_python(file_path, **kwargs)
    elif method == PlaybackMethod.EXPORT:
        return export_for_playback(file_path, file_path.parent, **kwargs)

    # Auto-select based on file type and available tools
    is_midi = file_path.suffix.lower() in [".mid", ".midi"]

    # Prefer python playback if available
    if check_pygame() or (is_midi and check_fluidsynth()):
        if is_midi:
            return play_with_fluidsynth(file_path, wait=False)
        return play_with_python(file_path)

    # Fall back to browser
    return play_with_browser(file_path)


def get_player_info() -> dict:
    """Get info about player capabilities."""
    return {
        "pygame_available": check_pygame(),
        "fluidsynth_available": check_fluidsynth(),
        "ffmpeg_available": check_ffmpeg(),
        "soundfont_found": find_soundfont() is not None,
        "browser_available": True,
        "recommended_method": (
            "python" if check_pygame() or check_fluidsynth()
            else "browser"
        )
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.player <file> [method]")
        print("Methods: browser, python, export")
        print("\nCapabilities:")
        info = get_player_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        sys.exit(1)

    file_path = sys.argv[1]
    method = None
    if len(sys.argv) > 2:
        method = PlaybackMethod(sys.argv[2])

    print(f"Playing: {file_path}")
    result = play(file_path, method)
    print(f"Result: {result.message}")
