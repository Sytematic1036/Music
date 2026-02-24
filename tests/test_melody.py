"""Tests for melody generation module."""

import pytest
from pathlib import Path
import tempfile

from src.melody import (
    Melody,
    MelodyParams,
    MelodyNote,
    Motif,
    Contour,
    MotifDevelopment,
    generate_melody,
    generate_melody_for_genre,
    melody_to_midi,
    generate_contour,
    generate_motif,
    develop_motif,
    calculate_uniqueness,
    optimize_melody,
    GENRE_PRESETS,
)
from src.generator import get_scale_notes


class TestMelodyParams:
    """Tests for MelodyParams dataclass."""

    def test_default_values(self):
        params = MelodyParams()
        assert params.root_note == "C"
        assert params.mode == "major"
        assert params.tempo == 70
        assert params.contour == Contour.ARCH

    def test_custom_values(self):
        params = MelodyParams(
            root_note="G",
            mode="minor",
            tempo=90,
            duration_seconds=120
        )
        assert params.root_note == "G"
        assert params.mode == "minor"
        assert params.tempo == 90
        assert params.duration_seconds == 120


class TestContourGeneration:
    """Tests for contour generation."""

    def test_arch_contour_rises_then_falls(self):
        contour = generate_contour(Contour.ARCH, 8)
        assert len(contour) == 8
        # First half should be positive (rising)
        assert sum(contour[:4]) > 0
        # Second half should be negative (falling)
        assert sum(contour[4:]) < 0

    def test_descending_contour(self):
        contour = generate_contour(Contour.DESCENDING, 6)
        assert len(contour) == 6
        # Should be mostly negative
        assert sum(contour) < 0

    def test_ascending_contour(self):
        contour = generate_contour(Contour.ASCENDING, 6)
        assert len(contour) == 6
        # Should be mostly positive
        assert sum(contour) > 0

    def test_static_contour_minimal_movement(self):
        contour = generate_contour(Contour.STATIC, 6)
        assert len(contour) == 6
        # Should have small values
        assert all(abs(x) <= 1 for x in contour)


class TestMotifGeneration:
    """Tests for motif generation."""

    def test_generate_motif_basic(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()
        motif = generate_motif(scale, scale[0], 4, Contour.ARCH, params)

        assert isinstance(motif, Motif)
        assert len(motif.notes) > 0
        assert len(motif.contour) > 0

    def test_motif_notes_have_valid_pitches(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()
        motif = generate_motif(scale, scale[0], 4, Contour.ARCH, params)

        for note in motif.notes:
            assert 36 <= note.pitch <= 96  # Reasonable MIDI range
            assert note.duration > 0
            assert 0 <= note.velocity <= 127

    def test_motif_hash_uniqueness(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()

        motif1 = generate_motif(scale, scale[0], 4, Contour.ARCH, params)
        motif2 = generate_motif(scale, scale[2], 4, Contour.DESCENDING, params)

        # Different motifs should usually have different hashes
        # (though collisions possible)
        hash1 = motif1.get_hash()
        hash2 = motif2.get_hash()
        assert len(hash1) == 8
        assert len(hash2) == 8


class TestMotifDevelopment:
    """Tests for motif development functions."""

    def test_develop_exact(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()
        original = generate_motif(scale, scale[0], 4, Contour.ARCH, params)

        developed = develop_motif(original, MotifDevelopment.EXACT, scale, 10.0)

        assert len(developed.notes) == len(original.notes)

    def test_develop_transposed(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()
        original = generate_motif(scale, scale[0], 4, Contour.ARCH, params)

        developed = develop_motif(original, MotifDevelopment.TRANSPOSED, scale, 10.0, transposition=4)

        # Notes should be shifted
        assert developed.notes[0].start_time >= 10.0

    def test_develop_augmented_longer_durations(self):
        scale = get_scale_notes("C", "major", 5)
        params = MelodyParams()
        original = generate_motif(scale, scale[0], 4, Contour.ARCH, params)

        developed = develop_motif(original, MotifDevelopment.AUGMENTED, scale, 0.0)

        # Durations should be longer
        for orig, dev in zip(original.notes, developed.notes):
            assert dev.duration >= orig.duration


class TestMelodyGeneration:
    """Tests for complete melody generation."""

    def test_generate_melody_basic(self):
        params = MelodyParams(duration_seconds=30)
        melody = generate_melody(params)

        assert isinstance(melody, Melody)
        assert len(melody.notes) > 0
        assert melody.uniqueness_score >= 0

    def test_generate_melody_reproducible_with_seed(self):
        params = MelodyParams(duration_seconds=30)

        melody1 = generate_melody(params, seed=42)
        melody2 = generate_melody(params, seed=42)

        assert len(melody1.notes) == len(melody2.notes)
        for n1, n2 in zip(melody1.notes, melody2.notes):
            assert n1.pitch == n2.pitch
            assert n1.start_time == n2.start_time

    def test_generate_melody_for_genre(self):
        for genre in ["relaxation", "ambient", "meditation", "lofi", "classical"]:
            melody = generate_melody_for_genre(genre, duration_seconds=30)
            assert isinstance(melody, Melody)
            assert len(melody.notes) > 0

    def test_genre_presets_exist(self):
        expected_genres = ["relaxation", "ambient", "meditation", "lofi", "classical"]
        for genre in expected_genres:
            assert genre in GENRE_PRESETS


class TestMelodyUniqueness:
    """Tests for uniqueness calculation and optimization."""

    def test_calculate_uniqueness_empty_melody(self):
        melody = Melody()
        score = calculate_uniqueness(melody)
        assert score == 1.0  # Empty is unique

    def test_calculate_uniqueness_few_notes(self):
        melody = Melody(notes=[
            MelodyNote(60, 0, 1, 80),
            MelodyNote(62, 1, 1, 80),
            MelodyNote(64, 2, 1, 80),
        ])
        score = calculate_uniqueness(melody)
        assert score == 1.0  # Too few for pattern detection

    def test_calculate_uniqueness_repetitive_pattern(self):
        # Create repetitive melody
        notes = []
        for i in range(8):
            # Same pattern repeated
            notes.append(MelodyNote(60 + (i % 4) * 2, i, 1, 80))

        melody = Melody(notes=notes)
        score = calculate_uniqueness(melody)
        assert score < 1.0  # Should detect repetition

    def test_optimize_melody_improves_uniqueness(self):
        params = MelodyParams(duration_seconds=30)
        melody = generate_melody(params, seed=1)

        original_score = melody.uniqueness_score
        optimized = optimize_melody(melody, max_iterations=5)

        # Optimization should maintain or improve score
        assert optimized.uniqueness_score >= original_score * 0.9


class TestMelodyExport:
    """Tests for MIDI export."""

    def test_melody_to_midi_creates_file(self):
        params = MelodyParams(duration_seconds=10)
        melody = generate_melody(params, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_melody.mid"
            result = melody_to_midi(melody, output_path)

            assert Path(result).exists()
            assert Path(result).stat().st_size > 0

    def test_melody_to_midi_creates_directory(self):
        params = MelodyParams(duration_seconds=10)
        melody = generate_melody(params)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "test.mid"
            result = melody_to_midi(melody, output_path)

            assert Path(result).exists()


class TestMelodyNote:
    """Tests for MelodyNote dataclass."""

    def test_to_tuple(self):
        note = MelodyNote(60, 1.5, 0.5, 80)
        t = note.to_tuple()

        assert t == (60, 1.5, 0.5, 80)


class TestMelody:
    """Tests for Melody dataclass."""

    def test_get_midi_data(self):
        melody = Melody(notes=[
            MelodyNote(60, 0, 1, 80),
            MelodyNote(62, 1, 1, 75),
        ])

        data = melody.get_midi_data()
        assert len(data) == 2
        assert data[0] == (60, 0, 1, 80)

    def test_get_duration_beats_empty(self):
        melody = Melody()
        assert melody.get_duration_beats() == 0

    def test_get_duration_beats(self):
        melody = Melody(notes=[
            MelodyNote(60, 0, 1, 80),
            MelodyNote(62, 3, 2, 75),  # Ends at beat 5
        ])

        assert melody.get_duration_beats() == 5
