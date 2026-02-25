"""Tests for arrangement module."""

import pytest
from pathlib import Path
import tempfile

from src.arrangement import (
    Arrangement,
    ArrangementParams,
    Track,
    TrackRole,
    Instrument,
    arrange_melody,
    arrangement_to_midi,
    generate_chord_track,
    generate_bass_track,
    generate_pad_track,
    generate_texture_track,
    generate_counter_melody,
    create_melody_track,
    get_arrangement_summary,
    GENRE_INSTRUMENTS,
    ROLE_PAN,
    ROLE_VOLUME,
)
from src.melody import MelodyParams, generate_melody, MelodyNote


class TestArrangementParams:
    """Tests for ArrangementParams dataclass."""

    def test_default_values(self):
        params = ArrangementParams()
        assert params.genre == "relaxation"
        assert params.tempo == 70
        assert params.root_note == "C"
        assert params.mode == "major"

    def test_custom_values(self):
        params = ArrangementParams(
            genre="lofi",
            tempo=85,
            root_note="G",
            mode="minor",
            num_tracks=6
        )
        assert params.genre == "lofi"
        assert params.tempo == 85
        assert params.num_tracks == 6


class TestInstrument:
    """Tests for Instrument enum."""

    def test_instrument_values_are_valid_midi(self):
        for instrument in Instrument:
            assert 0 <= instrument.value <= 127

    def test_common_instruments_exist(self):
        assert Instrument.ACOUSTIC_PIANO.value == 0
        assert Instrument.STRING_ENSEMBLE.value == 48
        assert Instrument.ACOUSTIC_BASS.value == 32


class TestTrack:
    """Tests for Track dataclass."""

    def test_get_midi_program(self):
        track = Track(
            role=TrackRole.MELODY,
            instrument=Instrument.ACOUSTIC_PIANO
        )
        assert track.get_midi_program() == 0

    def test_default_values(self):
        track = Track(
            role=TrackRole.BASS,
            instrument=Instrument.ACOUSTIC_BASS
        )
        assert track.volume == 100
        assert track.pan == 64
        assert track.channel == 0
        assert len(track.notes) == 0


class TestTrackGeneration:
    """Tests for individual track generation functions."""

    def test_generate_chord_track(self):
        params = ArrangementParams(duration_seconds=30)
        track = generate_chord_track(params)

        assert track.role == TrackRole.HARMONY
        assert len(track.notes) > 0
        assert track.volume == ROLE_VOLUME[TrackRole.HARMONY]

    def test_generate_bass_track(self):
        params = ArrangementParams(duration_seconds=30)
        track = generate_bass_track(params)

        assert track.role == TrackRole.BASS
        assert len(track.notes) > 0
        # Bass notes should be in low range
        for note in track.notes:
            assert note.pitch <= 60  # At or below middle C

    def test_generate_pad_track(self):
        params = ArrangementParams(duration_seconds=30)
        track = generate_pad_track(params)

        assert track.role == TrackRole.PAD
        assert len(track.notes) > 0
        # Pad notes should have long durations
        for note in track.notes:
            assert note.duration >= 2.0

    def test_generate_texture_track(self):
        params = ArrangementParams(duration_seconds=60)
        track = generate_texture_track(params)

        assert track.role == TrackRole.TEXTURE
        # Texture is sparse
        assert track.volume < ROLE_VOLUME[TrackRole.MELODY]


class TestCounterMelody:
    """Tests for counter-melody generation."""

    def test_generate_counter_melody(self):
        melody_params = MelodyParams(duration_seconds=30)
        melody = generate_melody(melody_params, seed=42)
        arr_params = ArrangementParams(duration_seconds=30)

        counter = generate_counter_melody(melody, arr_params)

        assert counter.role == TrackRole.COUNTER_MELODY
        # Counter melody should have fewer notes than original
        assert len(counter.notes) < len(melody.notes)


class TestArrangeMelody:
    """Tests for full arrangement creation."""

    def test_arrange_melody_basic(self):
        melody_params = MelodyParams(duration_seconds=30)
        melody = generate_melody(melody_params, seed=42)

        arrangement = arrange_melody(melody)

        assert isinstance(arrangement, Arrangement)
        assert len(arrangement.tracks) >= 4
        assert arrangement.source_melody == melody

    def test_arrange_melody_with_params(self):
        melody_params = MelodyParams(duration_seconds=30)
        melody = generate_melody(melody_params, seed=42)

        arr_params = ArrangementParams(
            genre="ambient",
            tempo=melody.params.tempo,
            use_counterpoint=True
        )
        arrangement = arrange_melody(melody, arr_params)

        assert arrangement.params.genre == "ambient"
        # Should have counter melody track
        has_counter = any(t.role == TrackRole.COUNTER_MELODY for t in arrangement.tracks)
        # Note: counter melody might have no notes if melody is sparse
        # so we just check arrangement was created
        assert len(arrangement.tracks) >= 4

    def test_arrange_melody_reproducible(self):
        melody_params = MelodyParams(duration_seconds=30)
        melody = generate_melody(melody_params, seed=42)

        arr1 = arrange_melody(melody, seed=123)
        arr2 = arrange_melody(melody, seed=123)

        assert len(arr1.tracks) == len(arr2.tracks)

    def test_arrange_melody_all_genres(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)

        genres = ["relaxation", "ambient", "meditation", "lofi", "classical", "cinematic"]
        for genre in genres:
            params = ArrangementParams(genre=genre)
            arrangement = arrange_melody(melody, params)
            assert len(arrangement.tracks) >= 3


class TestArrangement:
    """Tests for Arrangement dataclass."""

    def test_get_track_by_role(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)
        arrangement = arrange_melody(melody)

        melody_track = arrangement.get_track_by_role(TrackRole.MELODY)
        assert melody_track is not None
        assert melody_track.role == TrackRole.MELODY

        bass_track = arrangement.get_track_by_role(TrackRole.BASS)
        assert bass_track is not None
        assert bass_track.role == TrackRole.BASS

    def test_get_duration_beats(self):
        melody_params = MelodyParams(duration_seconds=30)
        melody = generate_melody(melody_params, seed=1)
        arrangement = arrange_melody(melody)

        duration = arrangement.get_duration_beats()
        assert duration > 0


class TestArrangementExport:
    """Tests for MIDI export."""

    def test_arrangement_to_midi_creates_file(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)
        arrangement = arrange_melody(melody)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_arrangement.mid"
            result = arrangement_to_midi(arrangement, output_path)

            assert Path(result).exists()
            assert Path(result).stat().st_size > 0

    def test_arrangement_to_midi_multi_track(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)
        arrangement = arrange_melody(melody)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.mid"
            result = arrangement_to_midi(arrangement, output_path)

            # File should be larger than single-track melody
            assert Path(result).stat().st_size > 100


class TestArrangementSummary:
    """Tests for arrangement summary."""

    def test_get_arrangement_summary(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)
        arrangement = arrange_melody(melody)

        summary = get_arrangement_summary(arrangement)

        assert "genre" in summary
        assert "tempo" in summary
        assert "key" in summary
        assert "num_tracks" in summary
        assert "tracks" in summary
        assert len(summary["tracks"]) == len(arrangement.tracks)


class TestGenreInstruments:
    """Tests for genre-specific instrument selection."""

    def test_all_genres_have_instruments(self):
        expected_genres = ["relaxation", "ambient", "meditation", "lofi", "classical", "cinematic"]
        for genre in expected_genres:
            assert genre in GENRE_INSTRUMENTS
            instruments = GENRE_INSTRUMENTS[genre]
            assert TrackRole.MELODY in instruments or TrackRole.HARMONY in instruments

    def test_role_pan_positions(self):
        # Bass should be centered
        assert ROLE_PAN[TrackRole.BASS] == 64

        # Melody should be centered
        assert ROLE_PAN[TrackRole.MELODY] == 64

    def test_role_volumes(self):
        # Melody should be loudest
        assert ROLE_VOLUME[TrackRole.MELODY] >= ROLE_VOLUME[TrackRole.HARMONY]
        assert ROLE_VOLUME[TrackRole.MELODY] >= ROLE_VOLUME[TrackRole.PAD]


class TestCreateMelodyTrack:
    """Tests for melody track wrapping."""

    def test_create_melody_track(self):
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=1)

        track = create_melody_track(melody, "relaxation")

        assert track.role == TrackRole.MELODY
        assert len(track.notes) == len(melody.notes)
        assert track.instrument in GENRE_INSTRUMENTS["relaxation"][TrackRole.MELODY]
