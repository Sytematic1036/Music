"""
Test 002: Categorization Logic

Tests the categorization logic for tempo, genre, mood, and source.
"""

import pytest

from src.organizer import (
    MusicOrganizer,
    TempoCategory,
    GenreCategory,
    MoodCategory,
    SourceCategory,
    TEMPO_SLOW_MAX,
    TEMPO_MEDIUM_MAX,
)


@pytest.fixture
def organizer():
    """Create a MusicOrganizer instance."""
    return MusicOrganizer()


class TestTempoCategorizatiion:
    """Tests for tempo-based categorization."""

    def test_slow_tempo_boundary(self, organizer):
        """Test that tempo < 80 BPM is categorized as SLOW."""
        assert organizer.categorize_by_tempo(79) == TempoCategory.SLOW
        assert organizer.categorize_by_tempo(60) == TempoCategory.SLOW
        assert organizer.categorize_by_tempo(40) == TempoCategory.SLOW

    def test_slow_tempo_exact_boundary(self, organizer):
        """Test exact boundary at 80 BPM."""
        assert organizer.categorize_by_tempo(TEMPO_SLOW_MAX) == TempoCategory.MEDIUM

    def test_medium_tempo_range(self, organizer):
        """Test that tempo 80-120 BPM is categorized as MEDIUM."""
        assert organizer.categorize_by_tempo(80) == TempoCategory.MEDIUM
        assert organizer.categorize_by_tempo(100) == TempoCategory.MEDIUM
        assert organizer.categorize_by_tempo(120) == TempoCategory.MEDIUM

    def test_fast_tempo(self, organizer):
        """Test that tempo > 120 BPM is categorized as FAST."""
        assert organizer.categorize_by_tempo(121) == TempoCategory.FAST
        assert organizer.categorize_by_tempo(140) == TempoCategory.FAST
        assert organizer.categorize_by_tempo(180) == TempoCategory.FAST

    def test_edge_case_very_slow(self, organizer):
        """Test very slow tempo."""
        assert organizer.categorize_by_tempo(1) == TempoCategory.SLOW

    def test_edge_case_very_fast(self, organizer):
        """Test very fast tempo."""
        assert organizer.categorize_by_tempo(300) == TempoCategory.FAST

    def test_float_tempo(self, organizer):
        """Test tempo with decimal values."""
        assert organizer.categorize_by_tempo(79.9) == TempoCategory.SLOW
        assert organizer.categorize_by_tempo(80.1) == TempoCategory.MEDIUM
        assert organizer.categorize_by_tempo(120.5) == TempoCategory.FAST


class TestGenreCategorization:
    """Tests for genre-based categorization."""

    def test_ambient_genre(self, organizer):
        """Test ambient and variations."""
        assert organizer.categorize_by_genre("ambient") == GenreCategory.AMBIENT
        assert organizer.categorize_by_genre("ambience") == GenreCategory.AMBIENT
        assert organizer.categorize_by_genre("atmospheric") == GenreCategory.AMBIENT

    def test_piano_genre(self, organizer):
        """Test piano and variations."""
        assert organizer.categorize_by_genre("piano") == GenreCategory.PIANO
        assert organizer.categorize_by_genre("classical") == GenreCategory.PIANO

    def test_nature_genre(self, organizer):
        """Test nature and variations."""
        assert organizer.categorize_by_genre("nature") == GenreCategory.NATURE
        assert organizer.categorize_by_genre("forest") == GenreCategory.NATURE
        assert organizer.categorize_by_genre("ocean") == GenreCategory.NATURE
        assert organizer.categorize_by_genre("rain") == GenreCategory.NATURE

    def test_electronic_genre(self, organizer):
        """Test electronic and variations."""
        assert organizer.categorize_by_genre("electronic") == GenreCategory.ELECTRONIC
        assert organizer.categorize_by_genre("synth") == GenreCategory.ELECTRONIC
        assert organizer.categorize_by_genre("edm") == GenreCategory.ELECTRONIC

    def test_unknown_genre_defaults_to_other(self, organizer):
        """Test that unknown genres default to OTHER."""
        assert organizer.categorize_by_genre("unknown") == GenreCategory.OTHER
        assert organizer.categorize_by_genre("rock") == GenreCategory.OTHER
        assert organizer.categorize_by_genre("jazz") == GenreCategory.OTHER

    def test_case_insensitive(self, organizer):
        """Test that genre matching is case-insensitive."""
        assert organizer.categorize_by_genre("AMBIENT") == GenreCategory.AMBIENT
        assert organizer.categorize_by_genre("Ambient") == GenreCategory.AMBIENT
        assert organizer.categorize_by_genre("Piano") == GenreCategory.PIANO

    def test_whitespace_handling(self, organizer):
        """Test that whitespace is trimmed."""
        assert organizer.categorize_by_genre("  ambient  ") == GenreCategory.AMBIENT
        assert organizer.categorize_by_genre("\tpiano\n") == GenreCategory.PIANO


class TestMoodCategorization:
    """Tests for mood-based categorization."""

    def test_calm_mood(self, organizer):
        """Test calm and variations."""
        assert organizer.categorize_by_mood("calm") == MoodCategory.CALM
        assert organizer.categorize_by_mood("peaceful") == MoodCategory.CALM
        assert organizer.categorize_by_mood("relaxing") == MoodCategory.CALM
        assert organizer.categorize_by_mood("soothing") == MoodCategory.CALM

    def test_energetic_mood(self, organizer):
        """Test energetic and variations."""
        assert organizer.categorize_by_mood("energetic") == MoodCategory.ENERGETIC
        assert organizer.categorize_by_mood("upbeat") == MoodCategory.ENERGETIC
        assert organizer.categorize_by_mood("exciting") == MoodCategory.ENERGETIC

    def test_focus_mood(self, organizer):
        """Test focus and variations."""
        assert organizer.categorize_by_mood("focus") == MoodCategory.FOCUS
        assert organizer.categorize_by_mood("concentration") == MoodCategory.FOCUS
        assert organizer.categorize_by_mood("study") == MoodCategory.FOCUS
        assert organizer.categorize_by_mood("work") == MoodCategory.FOCUS

    def test_melancholic_mood(self, organizer):
        """Test melancholic and variations."""
        assert organizer.categorize_by_mood("melancholic") == MoodCategory.MELANCHOLIC
        assert organizer.categorize_by_mood("sad") == MoodCategory.MELANCHOLIC
        assert organizer.categorize_by_mood("emotional") == MoodCategory.MELANCHOLIC

    def test_unknown_mood_defaults_to_calm(self, organizer):
        """Test that unknown moods default to CALM."""
        assert organizer.categorize_by_mood("unknown") == MoodCategory.CALM
        assert organizer.categorize_by_mood("random") == MoodCategory.CALM


class TestSourceCategorization:
    """Tests for source-based categorization."""

    def test_generated_source(self, organizer):
        """Test generated and variations."""
        assert organizer.categorize_by_source("generated") == SourceCategory.GENERATED
        assert organizer.categorize_by_source("ai") == SourceCategory.GENERATED
        assert organizer.categorize_by_source("midi") == SourceCategory.GENERATED

    def test_youtube_source(self, organizer):
        """Test youtube and variations."""
        assert organizer.categorize_by_source("youtube") == SourceCategory.YOUTUBE
        assert organizer.categorize_by_source("yt") == SourceCategory.YOUTUBE
        assert organizer.categorize_by_source("downloaded") == SourceCategory.YOUTUBE

    def test_original_source(self, organizer):
        """Test original and variations."""
        assert organizer.categorize_by_source("original") == SourceCategory.ORIGINAL
        assert organizer.categorize_by_source("custom") == SourceCategory.ORIGINAL
        assert organizer.categorize_by_source("recorded") == SourceCategory.ORIGINAL

    def test_unknown_source_defaults_to_original(self, organizer):
        """Test that unknown sources default to ORIGINAL."""
        assert organizer.categorize_by_source("unknown") == SourceCategory.ORIGINAL
        assert organizer.categorize_by_source("other") == SourceCategory.ORIGINAL
