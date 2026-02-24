"""
Test 001: Directory Structure

Tests that the MusicOrganizer correctly creates the directory structure
for organizing music files by tempo, genre, mood, and source.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.organizer import (
    MusicOrganizer,
    TempoCategory,
    GenreCategory,
    MoodCategory,
    SourceCategory,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def organizer(temp_dir):
    """Create a MusicOrganizer with temporary directory."""
    return MusicOrganizer(base_path=temp_dir / "music_library")


class TestDirectoryStructure:
    """Tests for directory structure creation."""

    def test_setup_creates_directories(self, organizer, temp_dir):
        """Test that setup_directories creates all required directories."""
        created_dirs = organizer.setup_directories()

        assert len(created_dirs) > 0
        assert all(d.exists() for d in created_dirs)

    def test_tempo_directories_exist(self, organizer):
        """Test that all tempo category directories are created."""
        organizer.setup_directories()

        for tempo in TempoCategory:
            dir_path = organizer.base_path / "by_tempo" / tempo.value
            assert dir_path.exists(), f"Missing tempo directory: {tempo.value}"

    def test_genre_directories_exist(self, organizer):
        """Test that all genre category directories are created."""
        organizer.setup_directories()

        for genre in GenreCategory:
            dir_path = organizer.base_path / "by_genre" / genre.value
            assert dir_path.exists(), f"Missing genre directory: {genre.value}"

    def test_mood_directories_exist(self, organizer):
        """Test that all mood category directories are created."""
        organizer.setup_directories()

        for mood in MoodCategory:
            dir_path = organizer.base_path / "by_mood" / mood.value
            assert dir_path.exists(), f"Missing mood directory: {mood.value}"

    def test_source_directories_exist(self, organizer):
        """Test that all source category directories are created."""
        organizer.setup_directories()

        for source in SourceCategory:
            dir_path = organizer.base_path / "by_source" / source.value
            assert dir_path.exists(), f"Missing source directory: {source.value}"

    def test_setup_is_idempotent(self, organizer):
        """Test that running setup multiple times doesn't cause errors."""
        organizer.setup_directories()
        # Create a test file in one directory
        test_file = organizer.base_path / "by_tempo" / "slow" / "test.txt"
        test_file.write_text("test")

        # Run setup again
        organizer.setup_directories()

        # File should still exist
        assert test_file.exists()

    def test_directory_count(self, organizer):
        """Test the total number of directories created."""
        created_dirs = organizer.setup_directories()

        expected_count = (
            len(TempoCategory) +
            len(GenreCategory) +
            len(MoodCategory) +
            len(SourceCategory)
        )

        assert len(created_dirs) == expected_count

    def test_nested_structure(self, organizer):
        """Test that the directory structure is correctly nested."""
        organizer.setup_directories()

        # Check parent directories exist
        assert (organizer.base_path / "by_tempo").exists()
        assert (organizer.base_path / "by_genre").exists()
        assert (organizer.base_path / "by_mood").exists()
        assert (organizer.base_path / "by_source").exists()

        # Check they are actually directories
        assert (organizer.base_path / "by_tempo").is_dir()
        assert (organizer.base_path / "by_genre").is_dir()
        assert (organizer.base_path / "by_mood").is_dir()
        assert (organizer.base_path / "by_source").is_dir()
