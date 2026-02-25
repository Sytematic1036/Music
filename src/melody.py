"""
Advanced melody generation module.

Implements best practices for melody composition:
- Contour-based generation (arch, descending, wave patterns)
- Motif development (repetition, variation, sequence)
- Uniqueness optimization (avoid repetitive patterns)
- Genre-aware melody characteristics
"""

import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .generator import NOTE_MAP, SCALES, get_scale_notes


class Contour(Enum):
    """Melodic contour types based on music theory best practices."""
    ARCH = "arch"           # Rise then fall (most common)
    DESCENDING = "descending"  # Gradual descent
    ASCENDING = "ascending"    # Gradual rise
    WAVE = "wave"           # Oscillating pattern
    STATIC = "static"       # Minimal movement


class MotifDevelopment(Enum):
    """Ways to develop a motif."""
    EXACT = "exact"         # Repeat exactly
    TRANSPOSED = "transposed"  # Move to different pitch
    INVERTED = "inverted"   # Flip intervals
    RETROGRADE = "retrograde"  # Reverse order
    AUGMENTED = "augmented"   # Longer durations
    DIMINISHED = "diminished"  # Shorter durations
    VARIED = "varied"       # Slight pitch variations


@dataclass
class MelodyParams:
    """Parameters for melody generation."""
    root_note: str = "C"
    mode: str = "major"
    tempo: int = 70
    duration_seconds: int = 60
    octave: int = 5

    # Melody characteristics
    contour: Contour = Contour.ARCH
    note_density: float = 0.5  # 0-1, how many notes per beat
    use_motifs: bool = True
    motif_length: int = 4  # Notes per motif
    development_probability: float = 0.6

    # Uniqueness
    max_repetition: int = 2  # Max times a pattern can repeat
    variation_amount: float = 0.3

    # Rhythm
    time_signature: tuple[int, int] = (4, 4)
    syncopation: float = 0.2  # 0-1, off-beat probability

    # Expression
    velocity_range: tuple[int, int] = (50, 80)
    legato: float = 0.7  # Note overlap factor


@dataclass
class MelodyNote:
    """A single note in a melody."""
    pitch: int          # MIDI note number
    start_time: float   # In beats
    duration: float     # In beats
    velocity: int       # 0-127

    def to_tuple(self) -> tuple:
        return (self.pitch, self.start_time, self.duration, self.velocity)


@dataclass
class Motif:
    """A melodic motif (short musical idea)."""
    notes: list[MelodyNote] = field(default_factory=list)
    contour: list[int] = field(default_factory=list)  # Intervals

    def get_hash(self) -> str:
        """Get unique hash for pattern detection."""
        intervals = []
        for i in range(1, len(self.notes)):
            intervals.append(self.notes[i].pitch - self.notes[i-1].pitch)
        return hashlib.md5(str(intervals).encode()).hexdigest()[:8]


@dataclass
class Melody:
    """Complete melody with notes and metadata."""
    notes: list[MelodyNote] = field(default_factory=list)
    motifs: list[Motif] = field(default_factory=list)
    params: MelodyParams = field(default_factory=MelodyParams)
    uniqueness_score: float = 0.0

    def get_midi_data(self) -> list[tuple]:
        """Get data for MIDI export."""
        return [note.to_tuple() for note in self.notes]

    def get_duration_beats(self) -> float:
        """Total duration in beats."""
        if not self.notes:
            return 0
        return max(n.start_time + n.duration for n in self.notes)


def generate_contour(contour_type: Contour, length: int) -> list[int]:
    """
    Generate interval pattern based on contour type.

    Best practice: Melodies should have clear directional movement.
    """
    if contour_type == Contour.ARCH:
        # Rise to middle, then fall
        mid = length // 2
        rise = [random.choice([1, 2, 3]) for _ in range(mid)]
        fall = [random.choice([-1, -2, -3]) for _ in range(length - mid)]
        return rise + fall

    elif contour_type == Contour.DESCENDING:
        return [random.choice([-1, -2, 0, -1]) for _ in range(length)]

    elif contour_type == Contour.ASCENDING:
        return [random.choice([1, 2, 0, 1]) for _ in range(length)]

    elif contour_type == Contour.WAVE:
        pattern = []
        direction = 1
        for i in range(length):
            if i % 3 == 0:
                direction *= -1
            pattern.append(direction * random.choice([1, 2]))
        return pattern

    else:  # STATIC
        return [random.choice([-1, 0, 1, 0]) for _ in range(length)]


def generate_motif(
    scale: list[int],
    start_pitch: int,
    length: int,
    contour_type: Contour,
    params: MelodyParams
) -> Motif:
    """
    Generate a melodic motif.

    Best practice: Motifs are the building blocks of memorable melodies.
    """
    notes = []
    contour = generate_contour(contour_type, length)

    current_pitch = start_pitch
    current_time = 0.0

    for i, interval in enumerate(contour):
        # Snap to scale
        target_pitch = current_pitch + interval
        closest_scale_pitch = min(scale, key=lambda x: abs(x - target_pitch))

        # Allow some out-of-scale notes for color
        if random.random() < 0.1:
            pitch = target_pitch
        else:
            pitch = closest_scale_pitch

        # Rhythm variation
        if random.random() < params.syncopation:
            duration = random.choice([0.5, 0.75])  # Syncopated
        else:
            duration = random.choice([0.5, 1.0, 1.5])  # On-beat

        velocity = random.randint(*params.velocity_range)

        notes.append(MelodyNote(
            pitch=pitch,
            start_time=current_time,
            duration=duration * params.legato,
            velocity=velocity
        ))

        current_pitch = pitch
        current_time += duration

    return Motif(notes=notes, contour=contour)


def develop_motif(
    motif: Motif,
    development: MotifDevelopment,
    scale: list[int],
    start_time: float,
    transposition: int = 0
) -> Motif:
    """
    Create a variation of a motif.

    Best practice: Develop motifs through transformation for coherence.
    """
    new_notes = []

    for i, note in enumerate(motif.notes):
        new_pitch = note.pitch
        new_duration = note.duration
        new_velocity = note.velocity

        if development == MotifDevelopment.TRANSPOSED:
            new_pitch += transposition
            # Snap to scale
            new_pitch = min(scale, key=lambda x: abs(x - new_pitch))

        elif development == MotifDevelopment.INVERTED:
            if i > 0:
                original_interval = note.pitch - motif.notes[i-1].pitch
                new_pitch = new_notes[-1].pitch - original_interval

        elif development == MotifDevelopment.RETROGRADE:
            # Will be reversed at the end
            pass

        elif development == MotifDevelopment.AUGMENTED:
            new_duration *= 1.5

        elif development == MotifDevelopment.DIMINISHED:
            new_duration *= 0.75

        elif development == MotifDevelopment.VARIED:
            if random.random() < 0.3:
                new_pitch += random.choice([-2, -1, 1, 2])
                new_pitch = min(scale, key=lambda x: abs(x - new_pitch))

        new_notes.append(MelodyNote(
            pitch=new_pitch,
            start_time=start_time + (note.start_time - motif.notes[0].start_time),
            duration=new_duration,
            velocity=new_velocity
        ))

    if development == MotifDevelopment.RETROGRADE:
        new_notes = list(reversed(new_notes))
        # Recalculate times
        total_duration = sum(n.duration for n in new_notes)
        current_time = start_time
        for note in new_notes:
            note.start_time = current_time
            current_time += note.duration

    return Motif(notes=new_notes, contour=motif.contour)


def calculate_uniqueness(melody: Melody) -> float:
    """
    Calculate how unique/non-repetitive a melody is.

    Returns score 0-1 where 1 is completely unique.
    """
    if len(melody.notes) < 4:
        return 1.0

    # Extract 4-note patterns
    patterns = []
    for i in range(len(melody.notes) - 3):
        intervals = []
        for j in range(3):
            intervals.append(melody.notes[i+j+1].pitch - melody.notes[i+j].pitch)
        patterns.append(tuple(intervals))

    if not patterns:
        return 1.0

    # Count unique patterns
    unique_patterns = len(set(patterns))
    total_patterns = len(patterns)

    return unique_patterns / total_patterns


def optimize_melody(melody: Melody, max_iterations: int = 10) -> Melody:
    """
    Optimize melody for uniqueness while preserving musicality.

    Best practice: Balance repetition (memorability) with variety (interest).
    """
    best_melody = melody
    best_score = calculate_uniqueness(melody)

    scale = get_scale_notes(melody.params.root_note, melody.params.mode, melody.params.octave)

    for _ in range(max_iterations):
        # Create variation
        new_melody = Melody(
            notes=list(melody.notes),
            motifs=list(melody.motifs),
            params=melody.params
        )

        # Randomly vary some notes
        num_changes = random.randint(1, max(1, len(new_melody.notes) // 4))
        indices = random.sample(range(len(new_melody.notes)), min(num_changes, len(new_melody.notes)))

        for idx in indices:
            note = new_melody.notes[idx]
            # Small pitch adjustment
            new_pitch = note.pitch + random.choice([-2, -1, 1, 2])
            new_pitch = min(scale, key=lambda x: abs(x - new_pitch))
            new_melody.notes[idx] = MelodyNote(
                pitch=new_pitch,
                start_time=note.start_time,
                duration=note.duration,
                velocity=note.velocity
            )

        new_score = calculate_uniqueness(new_melody)

        # Accept if better, or sometimes accept worse (simulated annealing)
        if new_score > best_score or random.random() < 0.1:
            best_melody = new_melody
            best_score = new_score

    best_melody.uniqueness_score = best_score
    return best_melody


def generate_melody(params: MelodyParams, seed: Optional[int] = None) -> Melody:
    """
    Generate a complete melody using best practices.

    Args:
        params: Melody generation parameters
        seed: Random seed for reproducibility

    Returns:
        Generated melody with notes and metadata
    """
    if seed is not None:
        random.seed(seed)

    scale = get_scale_notes(params.root_note, params.mode, params.octave)

    # Calculate total beats
    beats_per_measure = params.time_signature[0]
    total_beats = int(params.duration_seconds * params.tempo / 60)

    melody = Melody(params=params)
    current_time = 0.0
    motifs_used = []
    pattern_counts = {}

    # Generate initial motif
    initial_motif = generate_motif(
        scale=scale,
        start_pitch=scale[2],  # Start on 3rd degree (common practice)
        length=params.motif_length,
        contour_type=params.contour,
        params=params
    )
    motifs_used.append(initial_motif)

    while current_time < total_beats:
        # Decide: new motif or develop existing?
        if params.use_motifs and motifs_used and random.random() < params.development_probability:
            # Develop existing motif
            source_motif = random.choice(motifs_used)
            development = random.choice(list(MotifDevelopment))
            transposition = random.choice([0, 2, 4, 5, 7]) if development == MotifDevelopment.TRANSPOSED else 0

            motif = develop_motif(
                motif=source_motif,
                development=development,
                scale=scale,
                start_time=current_time,
                transposition=transposition
            )
        else:
            # Generate new motif
            # Vary contour for interest
            contour = random.choice(list(Contour)) if random.random() < 0.3 else params.contour
            start_pitch = melody.notes[-1].pitch if melody.notes else scale[2]

            motif = generate_motif(
                scale=scale,
                start_pitch=start_pitch,
                length=params.motif_length,
                contour_type=contour,
                params=params
            )
            motifs_used.append(motif)

        # Check repetition limit
        motif_hash = motif.get_hash()
        pattern_counts[motif_hash] = pattern_counts.get(motif_hash, 0) + 1

        if pattern_counts[motif_hash] <= params.max_repetition:
            # Adjust note times to current position
            for note in motif.notes:
                adjusted_note = MelodyNote(
                    pitch=note.pitch,
                    start_time=current_time + (note.start_time - motif.notes[0].start_time),
                    duration=note.duration,
                    velocity=note.velocity
                )
                melody.notes.append(adjusted_note)

            melody.motifs.append(motif)

        # Move forward
        motif_duration = sum(n.duration for n in motif.notes)
        current_time += max(motif_duration, beats_per_measure)

    # Optimize for uniqueness
    melody = optimize_melody(melody)

    return melody


def melody_to_midi(
    melody: Melody,
    output_path: str | Path,
    track: int = 0,
    channel: int = 0
) -> str:
    """
    Export melody to MIDI file.

    Args:
        melody: Generated melody
        output_path: Path to save MIDI file
        track: MIDI track number
        channel: MIDI channel

    Returns:
        Path to saved file
    """
    try:
        from midiutil import MIDIFile
    except ImportError:
        raise ImportError("midiutil required: pip install midiutil")

    midi = MIDIFile(1)
    midi.addTempo(track, 0, melody.params.tempo)

    for note in melody.notes:
        midi.addNote(
            track,
            channel,
            note.pitch,
            note.start_time,
            note.duration,
            note.velocity
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    return str(output_path)


# Genre-specific presets
GENRE_PRESETS = {
    "relaxation": MelodyParams(
        tempo=65,
        mode="major",
        contour=Contour.ARCH,
        note_density=0.4,
        syncopation=0.1,
        velocity_range=(40, 65),
        legato=0.9
    ),
    "ambient": MelodyParams(
        tempo=60,
        mode="dorian",
        contour=Contour.WAVE,
        note_density=0.3,
        syncopation=0.2,
        velocity_range=(35, 55),
        legato=1.0
    ),
    "meditation": MelodyParams(
        tempo=50,
        mode="pentatonic_major",
        contour=Contour.STATIC,
        note_density=0.2,
        syncopation=0.05,
        velocity_range=(30, 50),
        legato=1.0
    ),
    "lofi": MelodyParams(
        tempo=75,
        mode="minor",
        contour=Contour.DESCENDING,
        note_density=0.5,
        syncopation=0.4,
        velocity_range=(50, 75),
        legato=0.7
    ),
    "classical": MelodyParams(
        tempo=80,
        mode="major",
        contour=Contour.ARCH,
        note_density=0.6,
        syncopation=0.15,
        velocity_range=(45, 90),
        legato=0.8,
        use_motifs=True,
        development_probability=0.7
    )
}


def generate_melody_for_genre(
    genre: str,
    duration_seconds: int = 60,
    root_note: str = "C",
    seed: Optional[int] = None
) -> Melody:
    """
    Generate melody using genre-specific presets.

    Args:
        genre: Genre name (relaxation, ambient, meditation, lofi, classical)
        duration_seconds: Length of melody
        root_note: Root note/key
        seed: Random seed

    Returns:
        Generated melody
    """
    params = GENRE_PRESETS.get(genre, GENRE_PRESETS["relaxation"])
    params.duration_seconds = duration_seconds
    params.root_note = root_note

    return generate_melody(params, seed)


if __name__ == "__main__":
    import sys

    genre = sys.argv[1] if len(sys.argv) > 1 else "relaxation"
    output = sys.argv[2] if len(sys.argv) > 2 else "melody.mid"

    print(f"Generating {genre} melody...")
    melody = generate_melody_for_genre(genre, duration_seconds=60)

    print(f"Notes: {len(melody.notes)}")
    print(f"Motifs: {len(melody.motifs)}")
    print(f"Uniqueness: {melody.uniqueness_score:.2%}")

    path = melody_to_midi(melody, output)
    print(f"Saved: {path}")
