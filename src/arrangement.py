"""
Arrangement module for multi-track instrument layering.

Implements best practices for music arrangement:
- Genre-specific instrument selection
- Frequency spectrum distribution
- Dynamic layering (verse, chorus, bridge)
- Counterpoint and harmony generation
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .generator import NOTE_MAP, SCALES, CHORDS, PROGRESSIONS, get_scale_notes, get_chord_notes
from .melody import Melody, MelodyNote, MelodyParams


class Instrument(Enum):
    """General MIDI instrument categories with program numbers."""
    # Piano family (0-7)
    ACOUSTIC_PIANO = 0
    ELECTRIC_PIANO = 4
    HARPSICHORD = 6

    # Chromatic percussion (8-15)
    CELESTA = 8
    GLOCKENSPIEL = 9
    MUSIC_BOX = 10
    VIBRAPHONE = 11
    MARIMBA = 12

    # Organ (16-23)
    CHURCH_ORGAN = 19
    REED_ORGAN = 20

    # Guitar (24-31)
    ACOUSTIC_GUITAR = 25
    ELECTRIC_GUITAR_CLEAN = 27
    ELECTRIC_GUITAR_JAZZ = 26

    # Bass (32-39)
    ACOUSTIC_BASS = 32
    ELECTRIC_BASS = 33
    SYNTH_BASS = 38

    # Strings (40-47)
    VIOLIN = 40
    VIOLA = 41
    CELLO = 42
    CONTRABASS = 43
    STRINGS_TREMOLO = 44
    STRINGS_PIZZICATO = 45

    # Ensemble (48-55)
    STRING_ENSEMBLE = 48
    SYNTH_STRINGS = 50
    CHOIR_AAHS = 52
    VOICE_OOHS = 53

    # Brass (56-63)
    TRUMPET = 56
    FRENCH_HORN = 60

    # Reed (64-71)
    SOPRANO_SAX = 64
    ALTO_SAX = 65
    OBOE = 68
    CLARINET = 71

    # Pipe (72-79)
    FLUTE = 73
    PAN_FLUTE = 75

    # Synth lead (80-87)
    SYNTH_LEAD_SQUARE = 80
    SYNTH_LEAD_SAW = 81

    # Synth pad (88-95)
    SYNTH_PAD_NEW_AGE = 88
    SYNTH_PAD_WARM = 89
    SYNTH_PAD_CHOIR = 91
    SYNTH_PAD_HALO = 94

    # Ethnic (104-111)
    SITAR = 104
    KOTO = 107

    # Sound effects (120-127)
    SEASHORE = 122


class TrackRole(Enum):
    """Role of a track in the arrangement."""
    MELODY = "melody"
    HARMONY = "harmony"
    BASS = "bass"
    PAD = "pad"
    COUNTER_MELODY = "counter_melody"
    RHYTHM = "rhythm"
    TEXTURE = "texture"


@dataclass
class Track:
    """A single instrument track."""
    role: TrackRole
    instrument: Instrument
    notes: list[MelodyNote] = field(default_factory=list)
    channel: int = 0
    volume: int = 100  # 0-127
    pan: int = 64      # 0-127, 64=center
    octave_offset: int = 0

    def get_midi_program(self) -> int:
        return self.instrument.value


@dataclass
class ArrangementParams:
    """Parameters for arrangement generation."""
    genre: str = "relaxation"
    tempo: int = 70
    root_note: str = "C"
    mode: str = "major"
    duration_seconds: int = 120
    time_signature: tuple[int, int] = (4, 4)

    # Layering
    num_tracks: int = 5
    use_dynamics: bool = True  # Verse/chorus variation
    use_counterpoint: bool = True

    # Frequency distribution
    bass_range: tuple[int, int] = (2, 3)   # Octaves
    mid_range: tuple[int, int] = (4, 5)
    high_range: tuple[int, int] = (5, 6)


@dataclass
class Arrangement:
    """Complete multi-track arrangement."""
    tracks: list[Track] = field(default_factory=list)
    params: ArrangementParams = field(default_factory=ArrangementParams)
    source_melody: Optional[Melody] = None

    def get_track_by_role(self, role: TrackRole) -> Optional[Track]:
        for track in self.tracks:
            if track.role == role:
                return track
        return None

    def get_duration_beats(self) -> float:
        max_duration = 0
        for track in self.tracks:
            for note in track.notes:
                end = note.start_time + note.duration
                if end > max_duration:
                    max_duration = end
        return max_duration


# Genre-specific instrument configurations
GENRE_INSTRUMENTS = {
    "relaxation": {
        TrackRole.MELODY: [Instrument.ACOUSTIC_PIANO, Instrument.FLUTE, Instrument.VIBRAPHONE],
        TrackRole.HARMONY: [Instrument.STRING_ENSEMBLE, Instrument.SYNTH_PAD_WARM],
        TrackRole.BASS: [Instrument.ACOUSTIC_BASS, Instrument.CELLO],
        TrackRole.PAD: [Instrument.SYNTH_PAD_NEW_AGE, Instrument.SYNTH_PAD_HALO],
        TrackRole.TEXTURE: [Instrument.CELESTA, Instrument.MUSIC_BOX],
    },
    "ambient": {
        TrackRole.MELODY: [Instrument.SYNTH_PAD_HALO, Instrument.PAN_FLUTE],
        TrackRole.HARMONY: [Instrument.SYNTH_STRINGS, Instrument.SYNTH_PAD_CHOIR],
        TrackRole.BASS: [Instrument.SYNTH_BASS, Instrument.CONTRABASS],
        TrackRole.PAD: [Instrument.SYNTH_PAD_NEW_AGE, Instrument.SYNTH_PAD_WARM],
        TrackRole.TEXTURE: [Instrument.SEASHORE, Instrument.CHOIR_AAHS],
    },
    "meditation": {
        TrackRole.MELODY: [Instrument.PAN_FLUTE, Instrument.KOTO],
        TrackRole.HARMONY: [Instrument.SYNTH_PAD_CHOIR, Instrument.VOICE_OOHS],
        TrackRole.BASS: [Instrument.CONTRABASS],
        TrackRole.PAD: [Instrument.SYNTH_PAD_HALO, Instrument.SYNTH_PAD_NEW_AGE],
        TrackRole.TEXTURE: [Instrument.CELESTA, Instrument.GLOCKENSPIEL],
    },
    "lofi": {
        TrackRole.MELODY: [Instrument.ELECTRIC_PIANO, Instrument.VIBRAPHONE],
        TrackRole.HARMONY: [Instrument.ACOUSTIC_GUITAR, Instrument.ELECTRIC_GUITAR_JAZZ],
        TrackRole.BASS: [Instrument.ELECTRIC_BASS, Instrument.SYNTH_BASS],
        TrackRole.PAD: [Instrument.SYNTH_PAD_WARM],
        TrackRole.RHYTHM: [Instrument.ACOUSTIC_GUITAR],
        TrackRole.TEXTURE: [Instrument.MUSIC_BOX],
    },
    "classical": {
        TrackRole.MELODY: [Instrument.VIOLIN, Instrument.FLUTE, Instrument.OBOE],
        TrackRole.HARMONY: [Instrument.VIOLA, Instrument.STRING_ENSEMBLE],
        TrackRole.BASS: [Instrument.CELLO, Instrument.CONTRABASS],
        TrackRole.COUNTER_MELODY: [Instrument.CLARINET, Instrument.FRENCH_HORN],
        TrackRole.TEXTURE: [Instrument.HARPSICHORD],
    },
    "cinematic": {
        TrackRole.MELODY: [Instrument.FRENCH_HORN, Instrument.VIOLIN],
        TrackRole.HARMONY: [Instrument.STRING_ENSEMBLE, Instrument.CHOIR_AAHS],
        TrackRole.BASS: [Instrument.CONTRABASS, Instrument.CELLO],
        TrackRole.PAD: [Instrument.SYNTH_STRINGS, Instrument.SYNTH_PAD_WARM],
        TrackRole.TEXTURE: [Instrument.CELESTA, Instrument.GLOCKENSPIEL],
    }
}

# Pan positions for frequency separation
ROLE_PAN = {
    TrackRole.MELODY: 64,        # Center
    TrackRole.HARMONY: 80,       # Slightly right
    TrackRole.BASS: 64,          # Center (bass is always mono-centered)
    TrackRole.PAD: 48,           # Slightly left
    TrackRole.COUNTER_MELODY: 44,  # Left
    TrackRole.RHYTHM: 90,        # Right
    TrackRole.TEXTURE: 32,       # Far left
}

# Volume levels for mix balance
ROLE_VOLUME = {
    TrackRole.MELODY: 100,
    TrackRole.HARMONY: 75,
    TrackRole.BASS: 90,
    TrackRole.PAD: 60,
    TrackRole.COUNTER_MELODY: 70,
    TrackRole.RHYTHM: 65,
    TrackRole.TEXTURE: 45,
}


def generate_chord_track(
    params: ArrangementParams,
    role: TrackRole = TrackRole.HARMONY,
    octave: int = 4
) -> Track:
    """
    Generate chord/harmony track.

    Best practice: Chords provide harmonic foundation.
    """
    instrument_options = GENRE_INSTRUMENTS.get(params.genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(role, [Instrument.STRING_ENSEMBLE])
    instrument = random.choice(instruments)

    track = Track(
        role=role,
        instrument=instrument,
        channel=1,
        volume=ROLE_VOLUME.get(role, 75),
        pan=ROLE_PAN.get(role, 64)
    )

    scale = get_scale_notes(params.root_note, params.mode, octave)
    progression_options = PROGRESSIONS.get(params.mode, PROGRESSIONS["major"])
    progression = random.choice(progression_options)

    beats_per_measure = params.time_signature[0]
    total_beats = int(params.duration_seconds * params.tempo / 60)
    total_measures = total_beats // beats_per_measure

    current_beat = 0
    for measure in range(total_measures):
        chord_degree = progression[measure % len(progression)] - 1
        chord_root = scale[chord_degree % len(scale)]

        # Determine chord type
        if params.mode == "minor":
            chord_type = "minor7" if chord_degree in [0, 3, 4] else "major7"
        else:
            chord_type = "major7" if chord_degree in [0, 3, 4] else "minor7"

        chord_notes = get_chord_notes(chord_root, chord_type)

        # Add chord notes with slight humanization
        for i, note_pitch in enumerate(chord_notes):
            velocity = random.randint(50, 70)
            # Slight timing variation for humanization
            start_offset = random.uniform(-0.05, 0.05)

            track.notes.append(MelodyNote(
                pitch=note_pitch,
                start_time=current_beat + start_offset + (i * 0.02),  # Rolled chord
                duration=beats_per_measure * 0.95,
                velocity=velocity
            ))

        current_beat += beats_per_measure

    return track


def generate_bass_track(params: ArrangementParams) -> Track:
    """
    Generate bass track.

    Best practice: Bass provides harmonic root and rhythmic foundation.
    """
    instrument_options = GENRE_INSTRUMENTS.get(params.genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(TrackRole.BASS, [Instrument.ACOUSTIC_BASS])
    instrument = random.choice(instruments)

    track = Track(
        role=TrackRole.BASS,
        instrument=instrument,
        channel=2,
        volume=ROLE_VOLUME[TrackRole.BASS],
        pan=ROLE_PAN[TrackRole.BASS]
    )

    octave = random.randint(*params.bass_range)
    scale = get_scale_notes(params.root_note, params.mode, octave)
    progression_options = PROGRESSIONS.get(params.mode, PROGRESSIONS["major"])
    progression = random.choice(progression_options)

    beats_per_measure = params.time_signature[0]
    total_beats = int(params.duration_seconds * params.tempo / 60)
    total_measures = total_beats // beats_per_measure

    current_beat = 0
    for measure in range(total_measures):
        chord_degree = progression[measure % len(progression)] - 1
        bass_note = scale[chord_degree % len(scale)]

        # Bass pattern: root on 1, fifth on 3 (common pattern)
        patterns = [
            [(0, 1.5), (2, 1.5)],  # Simple
            [(0, 1.0), (1.5, 0.5), (2, 1.0), (3.5, 0.5)],  # Walking
            [(0, 2.0), (2.5, 1.5)],  # Half-time
        ]
        pattern = random.choice(patterns)

        fifth_offset = 7  # Perfect fifth

        for i, (beat_offset, duration) in enumerate(pattern):
            if current_beat + beat_offset >= total_beats:
                break

            # Alternate root and fifth
            pitch = bass_note if i % 2 == 0 else bass_note + fifth_offset
            velocity = random.randint(60, 85)

            track.notes.append(MelodyNote(
                pitch=pitch,
                start_time=current_beat + beat_offset,
                duration=duration,
                velocity=velocity
            ))

        current_beat += beats_per_measure

    return track


def generate_pad_track(params: ArrangementParams) -> Track:
    """
    Generate pad/sustain track.

    Best practice: Pads fill frequency gaps and create atmosphere.
    """
    instrument_options = GENRE_INSTRUMENTS.get(params.genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(TrackRole.PAD, [Instrument.SYNTH_PAD_WARM])
    instrument = random.choice(instruments)

    track = Track(
        role=TrackRole.PAD,
        instrument=instrument,
        channel=3,
        volume=ROLE_VOLUME[TrackRole.PAD],
        pan=ROLE_PAN[TrackRole.PAD]
    )

    octave = 4  # Mid-range for pads
    scale = get_scale_notes(params.root_note, params.mode, octave)
    progression_options = PROGRESSIONS.get(params.mode, PROGRESSIONS["major"])
    progression = random.choice(progression_options)

    beats_per_measure = params.time_signature[0]
    total_beats = int(params.duration_seconds * params.tempo / 60)
    total_measures = total_beats // beats_per_measure

    # Pads change every 2-4 measures for slow evolution
    measures_per_change = random.choice([2, 4])

    current_beat = 0
    for measure in range(0, total_measures, measures_per_change):
        chord_degree = progression[measure % len(progression)] - 1

        # Use wider voicing for pads (root + 5th + octave)
        root = scale[chord_degree % len(scale)]
        pad_notes = [root, root + 7, root + 12]

        # Soft attack, long sustain
        velocity = random.randint(35, 55)
        duration = beats_per_measure * measures_per_change * 0.98

        for pitch in pad_notes:
            track.notes.append(MelodyNote(
                pitch=pitch,
                start_time=current_beat,
                duration=duration,
                velocity=velocity
            ))

        current_beat += beats_per_measure * measures_per_change

    return track


def generate_counter_melody(
    melody: Melody,
    params: ArrangementParams
) -> Track:
    """
    Generate counter-melody based on main melody.

    Best practice: Counter-melody moves contrary to main melody.
    """
    instrument_options = GENRE_INSTRUMENTS.get(params.genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(TrackRole.COUNTER_MELODY,
                                          instrument_options.get(TrackRole.HARMONY, [Instrument.CLARINET]))
    instrument = random.choice(instruments)

    track = Track(
        role=TrackRole.COUNTER_MELODY,
        instrument=instrument,
        channel=4,
        volume=ROLE_VOLUME.get(TrackRole.COUNTER_MELODY, 70),
        pan=ROLE_PAN.get(TrackRole.COUNTER_MELODY, 44)
    )

    scale = get_scale_notes(params.root_note, params.mode, 4)

    # Generate counter-melody by inverting intervals
    last_pitch = scale[4]  # Start on 5th degree
    for i, note in enumerate(melody.notes):
        if i == 0:
            continue

        # Contrary motion
        original_interval = melody.notes[i].pitch - melody.notes[i-1].pitch
        counter_interval = -original_interval

        new_pitch = last_pitch + counter_interval
        # Snap to scale
        new_pitch = min(scale, key=lambda x: abs(x - new_pitch))

        # Only play every 2nd-3rd note for sparseness
        if random.random() < 0.4:
            velocity = random.randint(45, 65)
            track.notes.append(MelodyNote(
                pitch=new_pitch,
                start_time=note.start_time + random.uniform(0, 0.1),
                duration=note.duration * 0.9,
                velocity=velocity
            ))

        last_pitch = new_pitch

    return track


def generate_texture_track(params: ArrangementParams) -> Track:
    """
    Generate texture/embellishment track.

    Best practice: Texture adds sparkle without overwhelming.
    """
    instrument_options = GENRE_INSTRUMENTS.get(params.genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(TrackRole.TEXTURE, [Instrument.CELESTA])
    instrument = random.choice(instruments)

    track = Track(
        role=TrackRole.TEXTURE,
        instrument=instrument,
        channel=5,
        volume=ROLE_VOLUME.get(TrackRole.TEXTURE, 45),
        pan=ROLE_PAN.get(TrackRole.TEXTURE, 32)
    )

    octave = random.randint(*params.high_range)
    scale = get_scale_notes(params.root_note, params.mode, octave)

    total_beats = int(params.duration_seconds * params.tempo / 60)

    # Sparse, random high notes for texture
    current_beat = random.uniform(4, 8)
    while current_beat < total_beats:
        if random.random() < 0.3:  # 30% chance of note
            pitch = random.choice(scale)
            velocity = random.randint(30, 50)
            duration = random.choice([0.25, 0.5, 1.0])

            track.notes.append(MelodyNote(
                pitch=pitch,
                start_time=current_beat,
                duration=duration,
                velocity=velocity
            ))

        # Random spacing
        current_beat += random.uniform(2, 6)

    return track


def create_melody_track(melody: Melody, genre: str) -> Track:
    """
    Wrap melody in a track with appropriate instrument.
    """
    instrument_options = GENRE_INSTRUMENTS.get(genre, GENRE_INSTRUMENTS["relaxation"])
    instruments = instrument_options.get(TrackRole.MELODY, [Instrument.ACOUSTIC_PIANO])
    instrument = random.choice(instruments)

    return Track(
        role=TrackRole.MELODY,
        instrument=instrument,
        notes=list(melody.notes),
        channel=0,
        volume=ROLE_VOLUME[TrackRole.MELODY],
        pan=ROLE_PAN[TrackRole.MELODY]
    )


def arrange_melody(
    melody: Melody,
    params: Optional[ArrangementParams] = None,
    seed: Optional[int] = None
) -> Arrangement:
    """
    Create full arrangement from a melody.

    Args:
        melody: Source melody
        params: Arrangement parameters
        seed: Random seed

    Returns:
        Complete arrangement with multiple tracks
    """
    if seed is not None:
        random.seed(seed)

    if params is None:
        params = ArrangementParams(
            tempo=melody.params.tempo,
            root_note=melody.params.root_note,
            mode=melody.params.mode,
            duration_seconds=melody.params.duration_seconds
        )

    arrangement = Arrangement(params=params, source_melody=melody)

    # Add melody track
    melody_track = create_melody_track(melody, params.genre)
    arrangement.tracks.append(melody_track)

    # Add harmony
    harmony_track = generate_chord_track(params, TrackRole.HARMONY)
    arrangement.tracks.append(harmony_track)

    # Add bass
    bass_track = generate_bass_track(params)
    arrangement.tracks.append(bass_track)

    # Add pad
    pad_track = generate_pad_track(params)
    arrangement.tracks.append(pad_track)

    # Add counter-melody if enabled
    if params.use_counterpoint:
        counter_track = generate_counter_melody(melody, params)
        if counter_track.notes:
            arrangement.tracks.append(counter_track)

    # Add texture
    texture_track = generate_texture_track(params)
    arrangement.tracks.append(texture_track)

    return arrangement


def arrangement_to_midi(
    arrangement: Arrangement,
    output_path: str | Path
) -> str:
    """
    Export arrangement to MIDI file.

    Args:
        arrangement: Complete arrangement
        output_path: Path to save file

    Returns:
        Path to saved file
    """
    try:
        from midiutil import MIDIFile
    except ImportError:
        raise ImportError("midiutil required: pip install midiutil")

    num_tracks = len(arrangement.tracks)
    midi = MIDIFile(num_tracks)

    for track_idx, track in enumerate(arrangement.tracks):
        midi.addTempo(track_idx, 0, arrangement.params.tempo)
        midi.addProgramChange(track_idx, track.channel, 0, track.get_midi_program())

        # Add control changes for pan
        midi.addControllerEvent(track_idx, track.channel, 0, 10, track.pan)  # CC10 = pan

        for note in track.notes:
            midi.addNote(
                track_idx,
                track.channel,
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


def get_arrangement_summary(arrangement: Arrangement) -> dict:
    """Get summary info about arrangement."""
    return {
        "genre": arrangement.params.genre,
        "tempo": arrangement.params.tempo,
        "key": f"{arrangement.params.root_note} {arrangement.params.mode}",
        "num_tracks": len(arrangement.tracks),
        "tracks": [
            {
                "role": t.role.value,
                "instrument": t.instrument.name,
                "notes": len(t.notes),
                "channel": t.channel
            }
            for t in arrangement.tracks
        ],
        "duration_beats": arrangement.get_duration_beats()
    }


if __name__ == "__main__":
    import sys
    from .melody import generate_melody_for_genre

    genre = sys.argv[1] if len(sys.argv) > 1 else "relaxation"
    output = sys.argv[2] if len(sys.argv) > 2 else "arrangement.mid"

    print(f"Generating {genre} arrangement...")

    # Generate melody first
    melody = generate_melody_for_genre(genre, duration_seconds=60)
    print(f"Melody: {len(melody.notes)} notes")

    # Create arrangement
    params = ArrangementParams(
        genre=genre,
        tempo=melody.params.tempo,
        root_note=melody.params.root_note,
        mode=melody.params.mode,
        duration_seconds=60
    )
    arrangement = arrange_melody(melody, params)

    # Print summary
    summary = get_arrangement_summary(arrangement)
    print(f"Tracks: {summary['num_tracks']}")
    for track in summary['tracks']:
        print(f"  - {track['role']}: {track['instrument']} ({track['notes']} notes)")

    # Export
    path = arrangement_to_midi(arrangement, output)
    print(f"Saved: {path}")
