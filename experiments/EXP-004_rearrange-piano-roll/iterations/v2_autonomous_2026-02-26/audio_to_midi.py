"""
Audio to MIDI conversion using librosa.

Converts MP3/WAV files to MIDI by detecting:
1. Dominant pitch (melody line)
2. Onset events (note timing)
3. Harmonic content (chords - experimental)

Note: This is a simplified approach. For better polyphonic transcription,
consider using basic-pitch (requires Python < 3.13 and TensorFlow).
"""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import librosa
import numpy as np
from midiutil import MIDIFile


@dataclass
class DetectedNote:
    """A note detected from audio."""
    pitch: int          # MIDI pitch (0-127)
    start_time: float   # Start time in seconds
    duration: float     # Duration in seconds
    velocity: int       # Velocity (0-127)
    track: int          # Track/channel index
    name: str           # Note name (e.g., "C4")


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis."""
    notes: list[DetectedNote]
    tempo: float
    duration: float
    tracks: list[dict]  # Track metadata


def hz_to_midi(hz: float) -> int:
    """Convert frequency in Hz to MIDI note number."""
    if hz <= 0:
        return 0
    return int(round(69 + 12 * np.log2(hz / 440.0)))


def midi_to_name(midi_note: int) -> str:
    """Convert MIDI note number to note name."""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    name = note_names[midi_note % 12]
    return f"{name}{octave}"


def analyze_audio(
    audio_path: str | Path,
    min_note_duration: float = 0.1,
    velocity_threshold: float = 0.3,
    separate_tracks: bool = True
) -> AudioAnalysisResult:
    """
    Analyze audio file and extract MIDI notes.

    Args:
        audio_path: Path to MP3/WAV file
        min_note_duration: Minimum note duration in seconds
        velocity_threshold: Minimum amplitude threshold (0-1)
        separate_tracks: If True, create separate tracks for melody/harmony/bass

    Returns:
        AudioAnalysisResult with detected notes and metadata
    """
    audio_path = Path(audio_path)

    # Load audio
    y, sr = librosa.load(str(audio_path), sr=22050)
    duration = librosa.get_duration(y=y, sr=sr)

    # Estimate tempo
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0])

    # Separate harmonic and percussive
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    notes = []
    tracks = []

    # Track 1: Melody (dominant pitch from harmonic component)
    melody_notes = extract_melody(y_harmonic, sr, min_note_duration, velocity_threshold)
    for note in melody_notes:
        note.track = 0
    notes.extend(melody_notes)
    tracks.append({
        "index": 0,
        "name": "Melody",
        "color": "#e94560",
        "instrument": "lead"
    })

    if separate_tracks:
        # Track 2: Bass (low frequency content)
        bass_notes = extract_bass(y_harmonic, sr, min_note_duration, velocity_threshold)
        for note in bass_notes:
            note.track = 1
        notes.extend(bass_notes)
        tracks.append({
            "index": 1,
            "name": "Bass",
            "color": "#60a5fa",
            "instrument": "bass"
        })

        # Track 3: Chords/Harmony (experimental)
        chord_notes = extract_chords(y_harmonic, sr, min_note_duration)
        for note in chord_notes:
            note.track = 2
        notes.extend(chord_notes)
        tracks.append({
            "index": 2,
            "name": "Harmony",
            "color": "#4ade80",
            "instrument": "pad"
        })

    return AudioAnalysisResult(
        notes=notes,
        tempo=tempo,
        duration=duration,
        tracks=tracks
    )


def extract_melody(
    y: np.ndarray,
    sr: int,
    min_duration: float,
    velocity_threshold: float
) -> list[DetectedNote]:
    """Extract melody line using pitch tracking."""
    notes = []

    # Use piptrack for pitch detection
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, fmin=80, fmax=2000)

    # Get frame times
    times = librosa.times_like(pitches, sr=sr)
    hop_length = 512  # default hop length
    frame_duration = hop_length / sr

    # Track dominant pitch over time
    current_pitch = None
    note_start = None
    note_magnitudes = []

    for i in range(pitches.shape[1]):
        # Find dominant pitch in this frame
        mag_frame = magnitudes[:, i]
        if mag_frame.max() > velocity_threshold * mag_frame.max():
            pitch_idx = mag_frame.argmax()
            pitch_hz = pitches[pitch_idx, i]

            if pitch_hz > 0:
                midi_pitch = hz_to_midi(pitch_hz)

                # Clamp to reasonable range
                if 36 <= midi_pitch <= 96:  # C2 to C7
                    if current_pitch is None:
                        # Start new note
                        current_pitch = midi_pitch
                        note_start = times[i]
                        note_magnitudes = [mag_frame[pitch_idx]]
                    elif abs(midi_pitch - current_pitch) <= 2:
                        # Continue same note (allow small variations)
                        note_magnitudes.append(mag_frame[pitch_idx])
                    else:
                        # Pitch changed - end current note, start new
                        if note_start is not None:
                            duration = times[i] - note_start
                            if duration >= min_duration:
                                avg_mag = np.mean(note_magnitudes)
                                velocity = int(min(127, max(40, avg_mag * 200)))
                                notes.append(DetectedNote(
                                    pitch=current_pitch,
                                    start_time=note_start,
                                    duration=duration,
                                    velocity=velocity,
                                    track=0,
                                    name=midi_to_name(current_pitch)
                                ))

                        current_pitch = midi_pitch
                        note_start = times[i]
                        note_magnitudes = [mag_frame[pitch_idx]]
        else:
            # Silence - end current note
            if current_pitch is not None and note_start is not None:
                duration = times[i] - note_start
                if duration >= min_duration:
                    avg_mag = np.mean(note_magnitudes) if note_magnitudes else 0.5
                    velocity = int(min(127, max(40, avg_mag * 200)))
                    notes.append(DetectedNote(
                        pitch=current_pitch,
                        start_time=note_start,
                        duration=duration,
                        velocity=velocity,
                        track=0,
                        name=midi_to_name(current_pitch)
                    ))

            current_pitch = None
            note_start = None
            note_magnitudes = []

    # Handle last note
    if current_pitch is not None and note_start is not None:
        duration = times[-1] - note_start
        if duration >= min_duration:
            avg_mag = np.mean(note_magnitudes) if note_magnitudes else 0.5
            velocity = int(min(127, max(40, avg_mag * 200)))
            notes.append(DetectedNote(
                pitch=current_pitch,
                start_time=note_start,
                duration=duration,
                velocity=velocity,
                track=0,
                name=midi_to_name(current_pitch)
            ))

    return notes


def extract_bass(
    y: np.ndarray,
    sr: int,
    min_duration: float,
    velocity_threshold: float
) -> list[DetectedNote]:
    """Extract bass line (low frequency content)."""
    notes = []

    # Low-pass filter for bass
    y_bass = librosa.effects.preemphasis(y, coef=-0.97)  # Emphasize low frequencies

    # Pitch detection in bass range
    pitches, magnitudes = librosa.piptrack(y=y_bass, sr=sr, fmin=30, fmax=200)
    times = librosa.times_like(pitches, sr=sr)

    current_pitch = None
    note_start = None
    note_magnitudes = []

    for i in range(pitches.shape[1]):
        mag_frame = magnitudes[:, i]
        if mag_frame.max() > 0:
            pitch_idx = mag_frame.argmax()
            pitch_hz = pitches[pitch_idx, i]

            if pitch_hz > 0:
                midi_pitch = hz_to_midi(pitch_hz)

                # Bass range: E1 to E3
                if 28 <= midi_pitch <= 52:
                    if current_pitch is None:
                        current_pitch = midi_pitch
                        note_start = times[i]
                        note_magnitudes = [mag_frame[pitch_idx]]
                    elif abs(midi_pitch - current_pitch) <= 2:
                        note_magnitudes.append(mag_frame[pitch_idx])
                    else:
                        if note_start is not None:
                            duration = times[i] - note_start
                            if duration >= min_duration:
                                avg_mag = np.mean(note_magnitudes)
                                velocity = int(min(127, max(50, avg_mag * 150)))
                                notes.append(DetectedNote(
                                    pitch=current_pitch,
                                    start_time=note_start,
                                    duration=duration,
                                    velocity=velocity,
                                    track=1,
                                    name=midi_to_name(current_pitch)
                                ))

                        current_pitch = midi_pitch
                        note_start = times[i]
                        note_magnitudes = [mag_frame[pitch_idx]]
        else:
            if current_pitch is not None and note_start is not None:
                duration = times[i] - note_start
                if duration >= min_duration * 2:  # Bass notes are typically longer
                    avg_mag = np.mean(note_magnitudes) if note_magnitudes else 0.5
                    velocity = int(min(127, max(50, avg_mag * 150)))
                    notes.append(DetectedNote(
                        pitch=current_pitch,
                        start_time=note_start,
                        duration=duration,
                        velocity=velocity,
                        track=1,
                        name=midi_to_name(current_pitch)
                    ))

            current_pitch = None
            note_start = None
            note_magnitudes = []

    return notes


def extract_chords(
    y: np.ndarray,
    sr: int,
    min_duration: float
) -> list[DetectedNote]:
    """Extract chord notes using chroma features (experimental)."""
    notes = []

    # Compute chroma features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    times = librosa.times_like(chroma, sr=sr)

    # Find strong chroma bins
    threshold = 0.5 * chroma.max()

    # Simplified: extract dominant chord tones at regular intervals
    segment_length = int(sr * 0.5)  # 0.5 second segments
    hop = segment_length

    for i in range(0, len(y) - segment_length, hop):
        segment = y[i:i + segment_length]
        segment_chroma = librosa.feature.chroma_cqt(y=segment, sr=sr)
        avg_chroma = segment_chroma.mean(axis=1)

        # Find top 3 chroma bins
        top_bins = np.argsort(avg_chroma)[-3:]

        start_time = i / sr
        duration = segment_length / sr

        for bin_idx in top_bins:
            if avg_chroma[bin_idx] > 0.3:
                # Convert chroma bin to MIDI (use octave 4 as reference)
                midi_pitch = 60 + bin_idx  # C4 + chroma offset

                notes.append(DetectedNote(
                    pitch=midi_pitch,
                    start_time=start_time,
                    duration=duration,
                    velocity=int(avg_chroma[bin_idx] * 80 + 40),
                    track=2,
                    name=midi_to_name(midi_pitch)
                ))

    return notes


def notes_to_midi(
    notes: list[DetectedNote],
    tempo: float = 120.0,
    output_path: Optional[str | Path] = None
) -> bytes:
    """
    Convert detected notes to MIDI file.

    Args:
        notes: List of detected notes
        tempo: Tempo in BPM
        output_path: Optional path to save MIDI file

    Returns:
        MIDI file as bytes
    """
    # Group notes by track
    tracks_dict = {}
    for note in notes:
        if note.track not in tracks_dict:
            tracks_dict[note.track] = []
        tracks_dict[note.track].append(note)

    num_tracks = max(tracks_dict.keys()) + 1 if tracks_dict else 1
    midi = MIDIFile(num_tracks)

    for track_idx in range(num_tracks):
        midi.addTempo(track_idx, 0, tempo)

        track_notes = tracks_dict.get(track_idx, [])
        for note in track_notes:
            # Convert time from seconds to beats
            time_in_beats = note.start_time * (tempo / 60)
            duration_in_beats = note.duration * (tempo / 60)

            midi.addNote(
                track=track_idx,
                channel=track_idx,
                pitch=note.pitch,
                time=time_in_beats,
                duration=duration_in_beats,
                volume=note.velocity
            )

    # Write to bytes
    import io
    buffer = io.BytesIO()
    midi.writeFile(buffer)
    midi_bytes = buffer.getvalue()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(midi_bytes)

    return midi_bytes


def audio_to_midi_json(audio_path: str | Path) -> str:
    """
    Convert audio to MIDI and return JSON for browser consumption.

    Returns JSON with structure compatible with Tone.js/midi parser.
    """
    result = analyze_audio(audio_path)

    # Convert to JSON format matching Tone.js MIDI format
    # Ensure all numpy types are converted to Python types
    output = {
        "header": {
            "name": Path(audio_path).stem,
            "ppq": 480,
            "tempos": [{"bpm": float(result.tempo), "ticks": 0}],
            "timeSignatures": [{"beats": 4, "beatType": 4, "ticks": 0}]
        },
        "tracks": []
    }

    # Group notes by track
    for track_info in result.tracks:
        track_notes = [n for n in result.notes if n.track == track_info["index"]]

        track_data = {
            "name": track_info["name"],
            "channel": int(track_info["index"]),
            "notes": [
                {
                    "midi": int(note.pitch),
                    "name": str(note.name),
                    "time": float(note.start_time),
                    "duration": float(note.duration),
                    "velocity": float(note.velocity / 127.0)
                }
                for note in track_notes
            ],
            "color": track_info["color"]
        }
        output["tracks"].append(track_data)

    return json.dumps(output)


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audio_to_midi.py <audio_file> [output.mid]")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Analyzing: {audio_file}")
    result = analyze_audio(audio_file)

    print(f"Detected {len(result.notes)} notes")
    print(f"Tempo: {result.tempo:.1f} BPM")
    print(f"Duration: {result.duration:.1f} seconds")
    print(f"Tracks: {len(result.tracks)}")

    for track in result.tracks:
        track_notes = [n for n in result.notes if n.track == track["index"]]
        print(f"  - {track['name']}: {len(track_notes)} notes")

    if output_file:
        notes_to_midi(result.notes, result.tempo, output_file)
        print(f"Saved MIDI to: {output_file}")
    else:
        # Output JSON to stdout
        print("\nJSON output:")
        print(audio_to_midi_json(audio_file))
