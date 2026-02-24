"""
Test 003: File Operations

Tests file copying, moving, duplicate handling, and organization.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.organizer import MusicOrganizer


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def organizer(temp_dir):
    """Create a MusicOrganizer with temporary directory."""
    org = MusicOrganizer(base_path=temp_dir / "music_library")
    org.setup_directories()
    return org


@pytest.fixture
def dummy_audio_file(temp_dir):
    """Create a dummy audio file for testing."""
    file_path = temp_dir / "test_song.wav"
    # Create a minimal WAV file header (44 bytes)
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Chunk size (16)
        0x01, 0x00,              # Audio format (1 = PCM)
        0x01, 0x00,              # Channels (1 = mono)
        0x44, 0xAC, 0x00, 0x00,  # Sample rate (44100)
        0x88, 0x58, 0x01, 0x00,  # Byte rate
        0x02, 0x00,              # Block align
        0x10, 0x00,              # Bits per sample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Data size (0)
    ])
    file_path.write_bytes(wav_header)
    return file_path


@pytest.fixture
def multiple_dummy_files(temp_dir):
    """Create multiple dummy audio files."""
    files = []
    for i in range(3):
        file_path = temp_dir / f"song_{i}.wav"
        file_path.write_bytes(b"RIFF" + b"\x00" * 40)  # Minimal content
        files.append(file_path)
    return files


class TestFileOrganization:
    """Tests for organizing files into categories."""

    def test_organize_by_tempo(self, organizer, dummy_audio_file):
        """Test organizing a file by tempo."""
        destinations = organizer.organize_file(
            dummy_audio_file,
            tempo=75.0
        )

        assert "tempo" in destinations
        assert destinations["tempo"].exists()
        assert "slow" in str(destinations["tempo"])

    def test_organize_by_genre(self, organizer, dummy_audio_file):
        """Test organizing a file by genre."""
        destinations = organizer.organize_file(
            dummy_audio_file,
            genre="ambient"
        )

        assert "genre" in destinations
        assert destinations["genre"].exists()
        assert "ambient" in str(destinations["genre"])

    def test_organize_by_mood(self, organizer, dummy_audio_file):
        """Test organizing a file by mood."""
        destinations = organizer.organize_file(
            dummy_audio_file,
            mood="calm"
        )

        assert "mood" in destinations
        assert destinations["mood"].exists()
        assert "calm" in str(destinations["mood"])

    def test_organize_by_source(self, organizer, dummy_audio_file):
        """Test organizing a file by source."""
        destinations = organizer.organize_file(
            dummy_audio_file,
            source="generated"
        )

        assert "source" in destinations
        assert destinations["source"].exists()
        assert "generated" in str(destinations["source"])

    def test_organize_by_multiple_categories(self, organizer, dummy_audio_file):
        """Test organizing a file by multiple categories."""
        destinations = organizer.organize_file(
            dummy_audio_file,
            tempo=90.0,
            genre="piano",
            mood="focus",
            source="original"
        )

        assert len(destinations) == 4
        assert all(d.exists() for d in destinations.values())

    def test_original_file_preserved(self, organizer, dummy_audio_file):
        """Test that original file is preserved when copying."""
        original_content = dummy_audio_file.read_bytes()

        organizer.organize_file(dummy_audio_file, tempo=90.0, copy=True)

        assert dummy_audio_file.exists()
        assert dummy_audio_file.read_bytes() == original_content


class TestDuplicateHandling:
    """Tests for handling duplicate filenames."""

    def test_duplicate_gets_suffix(self, organizer, temp_dir):
        """Test that duplicate files get a numeric suffix."""
        # Create first file
        file1 = temp_dir / "song.wav"
        file1.write_bytes(b"content1")

        # Organize first file
        dest1 = organizer.organize_file(file1, tempo=90.0)

        # Create another file with same content but organize again
        # (simulating a duplicate being organized)
        file1.write_bytes(b"content2")  # Change content
        dest2 = organizer.organize_file(file1, tempo=90.0)

        # Both should exist with different names
        assert dest1["tempo"].exists()
        assert dest2["tempo"].exists()
        assert dest1["tempo"] != dest2["tempo"]
        assert "_1" in str(dest2["tempo"])

    def test_multiple_duplicates(self, organizer, temp_dir):
        """Test handling multiple duplicates."""
        destinations = []

        for i in range(5):
            file_path = temp_dir / f"original_{i}.wav"
            file_path.write_bytes(f"content{i}".encode())

            # Rename to same name
            target = temp_dir / "same_name.wav"
            if target.exists():
                target.unlink()
            file_path.rename(target)

            dest = organizer.organize_file(target, tempo=90.0)
            destinations.append(dest["tempo"])

        # All should exist with unique names
        assert len(set(destinations)) == 5
        assert all(d.exists() for d in destinations)


class TestFileNotFound:
    """Tests for handling missing files."""

    def test_missing_file_raises_error(self, organizer):
        """Test that organizing a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            organizer.organize_file(
                Path("/nonexistent/file.wav"),
                tempo=90.0
            )


class TestMetadata:
    """Tests for metadata handling."""

    def test_metadata_saved(self, organizer, dummy_audio_file, temp_dir):
        """Test that metadata is saved correctly."""
        organizer.organize_file(
            dummy_audio_file,
            tempo=85.0,
            genre="ambient",
            mood="calm",
            source="generated"
        )

        metadata_path = temp_dir / "metadata.json"
        organizer.save_metadata(metadata_path)

        assert metadata_path.exists()

    def test_metadata_loaded(self, organizer, dummy_audio_file, temp_dir):
        """Test that metadata can be loaded."""
        organizer.organize_file(
            dummy_audio_file,
            tempo=85.0,
            genre="ambient"
        )

        metadata_path = temp_dir / "metadata.json"
        organizer.save_metadata(metadata_path)

        # Create new organizer and load
        new_organizer = MusicOrganizer()
        new_organizer.load_metadata(metadata_path)

        # Check metadata was loaded
        assert str(dummy_audio_file) in new_organizer._metadata_cache


class TestCategoryStats:
    """Tests for category statistics."""

    def test_stats_empty_library(self, organizer):
        """Test stats on empty library."""
        stats = organizer.get_category_stats()

        assert "by_tempo" in stats
        assert "by_genre" in stats
        assert "by_mood" in stats
        assert "by_source" in stats

        # All should be zero
        assert all(v == 0 for v in stats["by_tempo"].values())

    def test_stats_after_organizing(self, organizer, dummy_audio_file):
        """Test stats after organizing files."""
        organizer.organize_file(dummy_audio_file, tempo=75.0)  # slow

        stats = organizer.get_category_stats()

        assert stats["by_tempo"]["slow"] == 1
        assert stats["by_tempo"]["medium"] == 0
        assert stats["by_tempo"]["fast"] == 0
