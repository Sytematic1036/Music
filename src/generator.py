"""
MIDI music generator module.

Generates procedural relaxation music based on analyzed features.
Uses midiutil to create MIDI files.
"""

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# MIDI note numbers for C4 (middle C) to C5
NOTE_MAP = {
    "C": 60, "C#": 61, "Db": 61,
    "D": 62, "D#": 63, "Eb": 63,
    "E": 64,
    "F": 65, "F#": 66, "Gb": 66,
    "G": 67, "G#": 68, "Ab": 68,
    "A": 69, "A#": 70, "Bb": 70,
    "B": 71
}

# Scale intervals (semitones from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

# Chord patterns (intervals from root)
CHORDS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "major7": [0, 4, 7, 11],
    "minor7": [0, 3, 7, 10],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
}

# Common relaxation chord progressions (Roman numerals as scale degrees)
PROGRESSIONS = {
    "major": [
        [1, 4, 5, 1],      # I - IV - V - I
        [1, 6, 4, 5],      # I - vi - IV - V
        [1, 5, 6, 4],      # I - V - vi - IV
        [1, 4, 1, 5],      # I - IV - I - V
    ],
    "minor": [
        [1, 4, 5, 1],      # i - iv - v - i
        [1, 6, 3, 7],      # i - VI - III - VII
        [1, 7, 6, 5],      # i - VII - VI - v
        [1, 4, 6, 5],      # i - iv - VI - v
    ]
}


@dataclass
class GenerationParams:
    """Parameters for music generation."""
    tempo: int = 60
    root_note: str = "C"
    mode: str = "major"
    duration_seconds: int = 120
    variation_amount: float = 0.3  # 0-1, how much to vary from source
    add_melody: bool = True
    add_bass: bool = True
    add_chords: bool = True
    melody_octave: int = 5
    bass_octave: int = 3
    chord_octave: int = 4
    time_signature: tuple[int, int] = (4, 4)


def get_scale_notes(root: str, mode: str, octave: int = 4) -> list[int]:
    """Get MIDI note numbers for a scale."""
    root_midi = NOTE_MAP.get(root, 60) + (octave - 4) * 12
    scale_intervals = SCALES.get(mode, SCALES["major"])
    return [root_midi + interval for interval in scale_intervals]


def get_chord_notes(root_midi: int, chord_type: str) -> list[int]:
    """Get MIDI note numbers for a chord."""
    intervals = CHORDS.get(chord_type, CHORDS["major"])
    return [root_midi + interval for interval in intervals]


def generate_relaxation_midi(
    params: GenerationParams,
    output_path: str | Path,
    seed: Optional[int] = None
) -> str:
    """
    Generate a relaxation music MIDI file.

    Args:
        params: Generation parameters
        output_path: Path to save the MIDI file
        seed: Random seed for reproducibility

    Returns:
        Path to the generated MIDI file
    """
    try:
        from midiutil import MIDIFile
    except ImportError:
        raise ImportError(
            "midiutil is required. Install with: pip install midiutil"
        )

    if seed is not None:
        random.seed(seed)

    # Create MIDI file with 3 tracks
    midi = MIDIFile(3, deinterleave=False)

    # Track names
    track_melody = 0
    track_chords = 1
    track_bass = 2

    # Set tempo and time signature
    midi.addTempo(track_melody, 0, params.tempo)

    # Calculate measures and beats
    beats_per_measure = params.time_signature[0]
    total_beats = int(params.duration_seconds * params.tempo / 60)
    total_measures = total_beats // beats_per_measure

    # Get scale notes
    scale = get_scale_notes(params.root_note, params.mode, params.melody_octave)
    bass_scale = get_scale_notes(params.root_note, params.mode, params.bass_octave)
    chord_scale = get_scale_notes(params.root_note, params.mode, params.chord_octave)

    # Choose chord progression
    progression_options = PROGRESSIONS.get(params.mode, PROGRESSIONS["major"])
    progression = random.choice(progression_options)

    # Generate music
    current_beat = 0

    for measure in range(total_measures):
        # Get chord for this measure
        chord_degree = progression[measure % len(progression)] - 1  # Convert to 0-indexed
        chord_root = chord_scale[chord_degree % len(chord_scale)]

        # Determine chord type based on mode and degree
        if params.mode == "minor":
            chord_type = "minor" if chord_degree in [0, 3, 4] else "major"
        else:
            chord_type = "major" if chord_degree in [0, 3, 4] else "minor"

        # Add variation
        if random.random() < params.variation_amount:
            chord_type = random.choice(["sus2", "sus4", chord_type])

        # Generate chords
        if params.add_chords:
            chord_notes = get_chord_notes(chord_root, chord_type)
            for note in chord_notes:
                # Play chord for whole measure
                velocity = random.randint(40, 60)  # Soft for relaxation
                midi.addNote(
                    track_chords,
                    0,  # channel
                    note,
                    current_beat,
                    beats_per_measure,
                    velocity
                )

        # Generate bass
        if params.add_bass:
            bass_note = bass_scale[chord_degree % len(bass_scale)]
            # Bass plays on beats 1 and 3
            for beat_offset in [0, 2]:
                if current_beat + beat_offset < total_beats:
                    velocity = random.randint(50, 70)
                    duration = 1.5 if random.random() < 0.3 else 1.0
                    midi.addNote(
                        track_bass,
                        0,
                        bass_note,
                        current_beat + beat_offset,
                        duration,
                        velocity
                    )

        # Generate melody
        if params.add_melody:
            # Relaxation melody: sparse, gentle notes from scale
            melody_beats = [0, 1, 2, 3]
            random.shuffle(melody_beats)
            # Only play on 1-2 beats per measure for sparse feel
            num_notes = random.randint(1, 2)

            for i in range(num_notes):
                beat_in_measure = melody_beats[i]

                # Choose note from scale, prefer chord tones
                if random.random() < 0.6:
                    # Use chord tone
                    note = chord_notes[random.randint(0, len(chord_notes) - 1)]
                    note = note + 12  # Move to melody octave
                else:
                    # Use scale tone
                    note = random.choice(scale)

                # Add variation to pitch
                if random.random() < params.variation_amount:
                    note += random.choice([-2, -1, 1, 2])

                velocity = random.randint(45, 65)
                duration = random.choice([0.5, 1.0, 1.5, 2.0])

                midi.addNote(
                    track_melody,
                    0,
                    note,
                    current_beat + beat_in_measure,
                    duration,
                    velocity
                )

        current_beat += beats_per_measure

    # Save MIDI file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    return str(output_path)


def generate_from_analysis(
    analysis_params: dict,
    output_path: str | Path,
    variation: float = 0.3,
    duration_override: Optional[int] = None
) -> str:
    """
    Generate MIDI based on analysis parameters from analyzer module.

    Args:
        analysis_params: Dict from analyzer.analyze_for_generation()
        output_path: Path to save MIDI file
        variation: How much to vary (0-1)
        duration_override: Override duration in seconds

    Returns:
        Path to generated MIDI file
    """
    params = GenerationParams(
        tempo=analysis_params.get("tempo", 60),
        root_note=analysis_params.get("root_note", "C"),
        mode=analysis_params.get("mode", "major"),
        duration_seconds=duration_override or int(analysis_params.get("suggested_duration", 120)),
        variation_amount=variation,
    )

    # Adjust parameters based on analysis
    if analysis_params.get("is_calm", True):
        params.tempo = min(params.tempo, 80)  # Keep tempo calm

    return generate_relaxation_midi(params, output_path)


def generate_variations(
    base_params: GenerationParams,
    output_dir: str | Path,
    num_variations: int = 3
) -> list[str]:
    """
    Generate multiple variations of a piece.

    Args:
        base_params: Base generation parameters
        output_dir: Directory to save files
        num_variations: Number of variations to generate

    Returns:
        List of paths to generated MIDI files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i in range(num_variations):
        # Vary parameters slightly
        varied_params = GenerationParams(
            tempo=base_params.tempo + random.randint(-5, 5),
            root_note=base_params.root_note,
            mode=base_params.mode,
            duration_seconds=base_params.duration_seconds,
            variation_amount=base_params.variation_amount + random.uniform(-0.1, 0.1),
        )

        output_path = output_dir / f"variation_{i + 1}.mid"
        generate_relaxation_midi(varied_params, output_path, seed=i)
        paths.append(str(output_path))

    return paths


if __name__ == "__main__":
    import sys

    output = sys.argv[1] if len(sys.argv) > 1 else "generated.mid"

    params = GenerationParams(
        tempo=70,
        root_note="C",
        mode="major",
        duration_seconds=60,
        variation_amount=0.2
    )

    print(f"Generating relaxation music...")
    path = generate_relaxation_midi(params, output)
    print(f"Generated: {path}")
