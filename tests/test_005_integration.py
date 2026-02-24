"""
Test 005: Integration Tests

Full integration tests combining multiple components.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from src.organizer import (
    MusicOrganizer,
    TempoCategory,
    GenreCategory,
    MoodCategory,
    SourceCategory,
    setup_test_structure,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def full_organizer(temp_dir):
    """Create a fully set up MusicOrganizer."""
    organizer = MusicOrganizer(base_path=temp_dir / "music_library")
    organizer.setup_directories()
    return organizer


@pytest.fixture
def sample_music_files(temp_dir):
    """Create a set of sample music files with various characteristics."""
    files = []
    metadata = [
        {"name": "calm_piano.wav", "tempo": 60, "genre": "piano", "mood": "calm", "source": "original"},
        {"name": "upbeat_electronic.wav", "tempo": 140, "genre": "electronic", "mood": "energetic", "source": "generated"},
        {"name": "focus_ambient.wav", "tempo": 90, "genre": "ambient", "mood": "focus", "source": "generated"},
        {"name": "nature_sounds.wav", "tempo": 0, "genre": "nature", "mood": "calm", "source": "youtube"},
        {"name": "sad_piano.wav", "tempo": 70, "genre": "piano", "mood": "melancholic", "source": "original"},
    ]

    for meta in metadata:
        file_path = temp_dir / meta["name"]
        # Create minimal WAV content
        file_path.write_bytes(b"RIFF" + b"\x00" * 40)
        files.append({"path": file_path, **meta})

    return files


class TestFullWorkflow:
    """Test complete workflows from setup to organization."""

    def test_complete_setup_and_organize(self, full_organizer, sample_music_files):
        """Test complete workflow: setup directories, organize files."""
        # Organize all sample files
        for file_info in sample_music_files:
            full_organizer.organize_file(
                file_info["path"],
                tempo=file_info["tempo"],
                genre=file_info["genre"],
                mood=file_info["mood"],
                source=file_info["source"]
            )

        # Check stats
        stats = full_organizer.get_category_stats()

        # We have 2 slow (60, 70), 1 medium (90), 1 fast (140), 1 with 0 tempo (slow)
        assert stats["by_tempo"]["slow"] == 3  # 60, 70, and 0 BPM
        assert stats["by_tempo"]["medium"] == 1  # 90 BPM
        assert stats["by_tempo"]["fast"] == 1  # 140 BPM

        # Genre distribution
        assert stats["by_genre"]["piano"] == 2
        assert stats["by_genre"]["ambient"] == 1
        assert stats["by_genre"]["electronic"] == 1
        assert stats["by_genre"]["nature"] == 1

    def test_metadata_persistence(self, full_organizer, sample_music_files, temp_dir):
        """Test that metadata persists across organizer instances."""
        # Organize files
        for file_info in sample_music_files:
            full_organizer.organize_file(
                file_info["path"],
                tempo=file_info["tempo"],
                genre=file_info["genre"]
            )

        # Save metadata
        metadata_path = temp_dir / "metadata.json"
        full_organizer.save_metadata(metadata_path)

        # Create new organizer and load metadata
        new_organizer = MusicOrganizer(base_path=temp_dir / "music_library")
        new_organizer.load_metadata(metadata_path)

        # Verify metadata loaded
        assert len(new_organizer._metadata_cache) == len(sample_music_files)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_organize_without_setup(self, temp_dir):
        """Test organizing without calling setup_directories first."""
        organizer = MusicOrganizer(base_path=temp_dir / "music_library")

        # Create a test file
        test_file = temp_dir / "test.wav"
        test_file.write_bytes(b"RIFF" + b"\x00" * 40)

        # Should still work - directories created on demand
        destinations = organizer.organize_file(test_file, tempo=90)

        assert "tempo" in destinations
        assert destinations["tempo"].exists()

    def test_organize_with_no_categories(self, full_organizer, temp_dir):
        """Test organizing a file with no category specified."""
        test_file = temp_dir / "test.wav"
        test_file.write_bytes(b"RIFF" + b"\x00" * 40)

        # No categories specified
        destinations = full_organizer.organize_file(test_file)

        # Should return empty dict
        assert destinations == {}

    def test_very_long_filename(self, full_organizer, temp_dir):
        """Test handling very long filenames (within Windows limits)."""
        # Windows has a 260 character path limit, so use a reasonable length
        # that won't exceed the limit when combined with the temp directory path
        max_safe_length = 50  # Safe for most systems
        long_name = "a" * max_safe_length + ".wav"
        test_file = temp_dir / long_name
        test_file.write_bytes(b"RIFF" + b"\x00" * 40)

        destinations = full_organizer.organize_file(test_file, tempo=90)

        assert "tempo" in destinations
        assert destinations["tempo"].exists()

    def test_special_characters_in_filename(self, full_organizer, temp_dir):
        """Test handling special characters in filenames."""
        special_name = "test (1) [copy] #2.wav"
        test_file = temp_dir / special_name
        test_file.write_bytes(b"RIFF" + b"\x00" * 40)

        destinations = full_organizer.organize_file(test_file, tempo=90)

        assert "tempo" in destinations
        assert destinations["tempo"].exists()


class TestSetupTestStructure:
    """Test the setup_test_structure helper function."""

    def test_creates_test_files(self, temp_dir):
        """Test that setup_test_structure creates expected test files."""
        test_dir = temp_dir / "tests"

        test_files = setup_test_structure(test_dir)

        assert len(test_files) == 5
        assert test_files[0].name == "directory_structure"
        assert test_files[1].name == "categorization_logic"
        assert test_files[2].name == "file_operations"
        assert test_files[3].name == "tempo_detection"
        assert test_files[4].name == "integration"

    def test_sequential_numbering(self, temp_dir):
        """Test that test files are sequentially numbered."""
        test_dir = temp_dir / "tests"

        test_files = setup_test_structure(test_dir)

        numbers = [tf.number for tf in test_files]
        assert numbers == [1, 2, 3, 4, 5]


class TestCategoryEnums:
    """Test that all category enums are properly defined."""

    def test_tempo_categories(self):
        """Test TempoCategory enum values."""
        assert TempoCategory.SLOW.value == "slow"
        assert TempoCategory.MEDIUM.value == "medium"
        assert TempoCategory.FAST.value == "fast"
        assert len(TempoCategory) == 3

    def test_genre_categories(self):
        """Test GenreCategory enum values."""
        expected = {"ambient", "piano", "nature", "electronic", "other"}
        actual = {g.value for g in GenreCategory}
        assert actual == expected

    def test_mood_categories(self):
        """Test MoodCategory enum values."""
        expected = {"calm", "energetic", "focus", "melancholic"}
        actual = {m.value for m in MoodCategory}
        assert actual == expected

    def test_source_categories(self):
        """Test SourceCategory enum values."""
        expected = {"generated", "youtube", "original"}
        actual = {s.value for s in SourceCategory}
        assert actual == expected
