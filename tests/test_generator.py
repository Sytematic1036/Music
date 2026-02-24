"""Tests for MIDI generator module."""

import pytest
from pathlib import Path

from src.generator import (
    GenerationParams,
    get_scale_notes,
    get_chord_notes,
    generate_relaxation_midi,
    generate_from_analysis,
    NOTE_MAP,
    SCALES,
)


class TestNoteMapping:
    """Tests for note and scale functions."""

    def test_note_map_contains_all_notes(self):
        expected_notes = ["C", "D", "E", "F", "G", "A", "B"]
        for note in expected_notes:
            assert note in NOTE_MAP

    def test_c4_is_60(self):
        assert NOTE_MAP["C"] == 60

    def test_scale_intervals(self):
        assert SCALES["major"] == [0, 2, 4, 5, 7, 9, 11]
        assert SCALES["minor"] == [0, 2, 3, 5, 7, 8, 10]


class TestGetScaleNotes:
    """Tests for get_scale_notes function."""

    def test_c_major_scale(self):
        notes = get_scale_notes("C", "major", octave=4)
        assert notes[0] == 60  # C4
        assert notes[2] == 64  # E4
        assert notes[4] == 67  # G4

    def test_different_octave(self):
        notes_4 = get_scale_notes("C", "major", octave=4)
        notes_5 = get_scale_notes("C", "major", octave=5)
        assert notes_5[0] - notes_4[0] == 12  # One octave higher


class TestGetChordNotes:
    """Tests for get_chord_notes function."""

    def test_major_chord(self):
        notes = get_chord_notes(60, "major")  # C major
        assert notes == [60, 64, 67]  # C, E, G

    def test_minor_chord(self):
        notes = get_chord_notes(60, "minor")  # C minor
        assert notes == [60, 63, 67]  # C, Eb, G


class TestGenerationParams:
    """Tests for GenerationParams dataclass."""

    def test_default_values(self):
        params = GenerationParams()
        assert params.tempo == 60
        assert params.root_note == "C"
        assert params.mode == "major"
        assert params.add_melody is True

    def test_custom_values(self):
        params = GenerationParams(
            tempo=80,
            root_note="G",
            mode="minor",
            duration_seconds=90
        )
        assert params.tempo == 80
        assert params.root_note == "G"
        assert params.mode == "minor"


class TestGenerateRelaxationMidi:
    """Tests for MIDI generation function."""

    def test_generates_midi_file(self, tmp_path):
        """Test that a valid MIDI file is generated."""
        output_path = tmp_path / "test.mid"

        params = GenerationParams(
            tempo=70,
            root_note="C",
            mode="major",
            duration_seconds=30,
            variation_amount=0.2
        )

        result_path = generate_relaxation_midi(params, output_path)

        assert Path(result_path).exists()
        assert Path(result_path).suffix == ".mid"

        # Check file is not empty
        assert Path(result_path).stat().st_size > 0

    def test_reproducible_with_seed(self, tmp_path):
        """Test that same seed produces same output."""
        path1 = tmp_path / "test1.mid"
        path2 = tmp_path / "test2.mid"

        params = GenerationParams(duration_seconds=10)

        generate_relaxation_midi(params, path1, seed=42)
        generate_relaxation_midi(params, path2, seed=42)

        # Same seed should produce same file
        assert path1.read_bytes() == path2.read_bytes()

    def test_different_seeds_different_output(self, tmp_path):
        """Test that different seeds produce different output."""
        path1 = tmp_path / "test1.mid"
        path2 = tmp_path / "test2.mid"

        params = GenerationParams(duration_seconds=30)

        generate_relaxation_midi(params, path1, seed=1)
        generate_relaxation_midi(params, path2, seed=2)

        # Different seeds should (usually) produce different files
        # Note: Very short durations might coincidentally match
        assert path1.read_bytes() != path2.read_bytes()


class TestGenerateFromAnalysis:
    """Tests for generate_from_analysis function."""

    def test_generates_from_params(self, tmp_path):
        """Test generation from analysis parameters."""
        analysis_params = {
            "tempo": 75,
            "root_note": "A",
            "mode": "minor",
            "is_calm": True,
            "suggested_duration": 60
        }

        output_path = tmp_path / "from_analysis.mid"
        result = generate_from_analysis(
            analysis_params,
            output_path,
            variation=0.3
        )

        assert Path(result).exists()

    def test_duration_override(self, tmp_path):
        """Test that duration can be overridden."""
        analysis_params = {
            "tempo": 70,
            "root_note": "C",
            "mode": "major",
            "suggested_duration": 300
        }

        output_path = tmp_path / "short.mid"
        generate_from_analysis(
            analysis_params,
            output_path,
            duration_override=30
        )

        # File should exist (exact duration verification would need MIDI parsing)
        assert Path(output_path).exists()
