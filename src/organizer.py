"""
Music Test Organizer module.

Provides functionality for:
1. Creating organized directory structures for music tests
2. Categorizing music files by tempo, genre, mood, and source
3. Managing test files with sequential numbering (test_001_, test_002_, etc.)

Usage:
    from src.organizer import MusicOrganizer, TempoCategory, MoodCategory

    organizer = MusicOrganizer(base_path="music_library")
    organizer.setup_directories()

    # Categorize by tempo
    category = organizer.categorize_by_tempo(85.0)  # Returns TempoCategory.MEDIUM

    # Organize a file
    organizer.organize_file("song.wav", tempo=85.0, genre="ambient", mood="calm")
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class TempoCategory(Enum):
    """Tempo categories based on BPM."""
    SLOW = "slow"       # < 80 BPM
    MEDIUM = "medium"   # 80-120 BPM
    FAST = "fast"       # > 120 BPM


class MoodCategory(Enum):
    """Mood categories for music."""
    CALM = "calm"
    ENERGETIC = "energetic"
    FOCUS = "focus"
    MELANCHOLIC = "melancholic"


class GenreCategory(Enum):
    """Genre categories for music."""
    AMBIENT = "ambient"
    PIANO = "piano"
    NATURE = "nature"
    ELECTRONIC = "electronic"
    OTHER = "other"


class SourceCategory(Enum):
    """Source categories for music files."""
    GENERATED = "generated"
    YOUTUBE = "youtube"
    ORIGINAL = "original"


# Tempo thresholds
TEMPO_SLOW_MAX = 80
TEMPO_MEDIUM_MAX = 120


@dataclass
class FileMetadata:
    """Metadata for a music file."""
    filename: str
    filepath: str
    tempo: Optional[float] = None
    genre: Optional[str] = None
    mood: Optional[str] = None
    source: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    test_number: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "filepath": self.filepath,
            "tempo": self.tempo,
            "genre": self.genre,
            "mood": self.mood,
            "source": self.source,
            "created_at": self.created_at,
            "test_number": self.test_number
        }


@dataclass
class TestFileInfo:
    """Represents a test file with sequential numbering."""
    number: int
    name: str
    description: str
    path: Path

    @property
    def prefix(self) -> str:
        """Get the test prefix (e.g., 'test_001')."""
        return f"test_{self.number:03d}"

    @property
    def full_name(self) -> str:
        """Get full test name (e.g., 'test_001_basic_structure')."""
        return f"{self.prefix}_{self.name}"


# Alias for backwards compatibility
TestFile = TestFileInfo


class MusicOrganizer:
    """
    Organizes music files into categorized directories and manages test files.

    Directory structure created:
        base_path/
        ├── by_genre/
        │   ├── ambient/
        │   ├── piano/
        │   ├── nature/
        │   └── electronic/
        ├── by_tempo/
        │   ├── slow/
        │   ├── medium/
        │   └── fast/
        ├── by_mood/
        │   ├── calm/
        │   ├── energetic/
        │   ├── focus/
        │   └── melancholic/
        └── by_source/
            ├── generated/
            ├── youtube/
            └── original/
    """

    def __init__(self, base_path: str | Path = "music_library"):
        """
        Initialize the organizer.

        Args:
            base_path: Base directory for the music library
        """
        self.base_path = Path(base_path)
        self._metadata_cache: dict[str, FileMetadata] = {}
        self._next_test_number = 1

    def setup_directories(self) -> list[Path]:
        """
        Create the complete directory structure.

        Returns:
            List of created directories
        """
        created_dirs = []

        # Genre directories
        for genre in GenreCategory:
            dir_path = self.base_path / "by_genre" / genre.value
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path)

        # Tempo directories
        for tempo in TempoCategory:
            dir_path = self.base_path / "by_tempo" / tempo.value
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path)

        # Mood directories
        for mood in MoodCategory:
            dir_path = self.base_path / "by_mood" / mood.value
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path)

        # Source directories
        for source in SourceCategory:
            dir_path = self.base_path / "by_source" / source.value
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path)

        return created_dirs

    def categorize_by_tempo(self, bpm: float) -> TempoCategory:
        """
        Categorize music by tempo (BPM).

        Args:
            bpm: Beats per minute

        Returns:
            TempoCategory enum value
        """
        if bpm < TEMPO_SLOW_MAX:
            return TempoCategory.SLOW
        elif bpm <= TEMPO_MEDIUM_MAX:
            return TempoCategory.MEDIUM
        else:
            return TempoCategory.FAST

    def categorize_by_genre(self, genre: str) -> GenreCategory:
        """
        Categorize music by genre string.

        Args:
            genre: Genre name (case-insensitive)

        Returns:
            GenreCategory enum value
        """
        genre_lower = genre.lower().strip()

        # Map common variations
        genre_mapping = {
            "ambient": GenreCategory.AMBIENT,
            "ambience": GenreCategory.AMBIENT,
            "atmospheric": GenreCategory.AMBIENT,
            "piano": GenreCategory.PIANO,
            "classical": GenreCategory.PIANO,
            "nature": GenreCategory.NATURE,
            "natural": GenreCategory.NATURE,
            "forest": GenreCategory.NATURE,
            "ocean": GenreCategory.NATURE,
            "rain": GenreCategory.NATURE,
            "electronic": GenreCategory.ELECTRONIC,
            "synth": GenreCategory.ELECTRONIC,
            "edm": GenreCategory.ELECTRONIC,
        }

        return genre_mapping.get(genre_lower, GenreCategory.OTHER)

    def categorize_by_mood(self, mood: str) -> MoodCategory:
        """
        Categorize music by mood string.

        Args:
            mood: Mood name (case-insensitive)

        Returns:
            MoodCategory enum value
        """
        mood_lower = mood.lower().strip()

        mood_mapping = {
            "calm": MoodCategory.CALM,
            "peaceful": MoodCategory.CALM,
            "relaxing": MoodCategory.CALM,
            "soothing": MoodCategory.CALM,
            "energetic": MoodCategory.ENERGETIC,
            "upbeat": MoodCategory.ENERGETIC,
            "exciting": MoodCategory.ENERGETIC,
            "focus": MoodCategory.FOCUS,
            "concentration": MoodCategory.FOCUS,
            "study": MoodCategory.FOCUS,
            "work": MoodCategory.FOCUS,
            "melancholic": MoodCategory.MELANCHOLIC,
            "sad": MoodCategory.MELANCHOLIC,
            "emotional": MoodCategory.MELANCHOLIC,
        }

        return mood_mapping.get(mood_lower, MoodCategory.CALM)

    def categorize_by_source(self, source: str) -> SourceCategory:
        """
        Categorize music by source string.

        Args:
            source: Source name (case-insensitive)

        Returns:
            SourceCategory enum value
        """
        source_lower = source.lower().strip()

        source_mapping = {
            "generated": SourceCategory.GENERATED,
            "ai": SourceCategory.GENERATED,
            "midi": SourceCategory.GENERATED,
            "youtube": SourceCategory.YOUTUBE,
            "yt": SourceCategory.YOUTUBE,
            "downloaded": SourceCategory.YOUTUBE,
            "original": SourceCategory.ORIGINAL,
            "custom": SourceCategory.ORIGINAL,
            "recorded": SourceCategory.ORIGINAL,
        }

        return source_mapping.get(source_lower, SourceCategory.ORIGINAL)

    def _get_unique_filename(self, directory: Path, filename: str) -> str:
        """
        Get a unique filename in the directory, adding suffix if needed.

        Args:
            directory: Target directory
            filename: Original filename

        Returns:
            Unique filename (may have _1, _2, etc. suffix)
        """
        path = directory / filename
        if not path.exists():
            return filename

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            if not (directory / new_name).exists():
                return new_name
            counter += 1

    def organize_file(
        self,
        source_path: str | Path,
        tempo: Optional[float] = None,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        source: Optional[str] = None,
        copy: bool = True
    ) -> dict[str, Path]:
        """
        Organize a file into appropriate categories.

        Args:
            source_path: Path to the source file
            tempo: BPM (if known)
            genre: Genre name
            mood: Mood name
            source: Source type
            copy: If True, copy file; if False, move file

        Returns:
            Dictionary mapping category type to destination path
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        destinations = {}
        filename = source_path.name

        # Organize by tempo
        if tempo is not None:
            tempo_cat = self.categorize_by_tempo(tempo)
            dest_dir = self.base_path / "by_tempo" / tempo_cat.value
            dest_dir.mkdir(parents=True, exist_ok=True)
            unique_name = self._get_unique_filename(dest_dir, filename)
            dest_path = dest_dir / unique_name

            if copy:
                shutil.copy2(source_path, dest_path)
            else:
                shutil.move(str(source_path), dest_path)
            destinations["tempo"] = dest_path

        # Organize by genre
        if genre is not None:
            genre_cat = self.categorize_by_genre(genre)
            dest_dir = self.base_path / "by_genre" / genre_cat.value
            dest_dir.mkdir(parents=True, exist_ok=True)
            unique_name = self._get_unique_filename(dest_dir, filename)
            dest_path = dest_dir / unique_name

            if copy:
                shutil.copy2(source_path, dest_path)
            destinations["genre"] = dest_path

        # Organize by mood
        if mood is not None:
            mood_cat = self.categorize_by_mood(mood)
            dest_dir = self.base_path / "by_mood" / mood_cat.value
            dest_dir.mkdir(parents=True, exist_ok=True)
            unique_name = self._get_unique_filename(dest_dir, filename)
            dest_path = dest_dir / unique_name

            if copy:
                shutil.copy2(source_path, dest_path)
            destinations["mood"] = dest_path

        # Organize by source
        if source is not None:
            source_cat = self.categorize_by_source(source)
            dest_dir = self.base_path / "by_source" / source_cat.value
            dest_dir.mkdir(parents=True, exist_ok=True)
            unique_name = self._get_unique_filename(dest_dir, filename)
            dest_path = dest_dir / unique_name

            if copy:
                shutil.copy2(source_path, dest_path)
            destinations["source"] = dest_path

        # Store metadata
        metadata = FileMetadata(
            filename=filename,
            filepath=str(source_path),
            tempo=tempo,
            genre=genre,
            mood=mood,
            source=source
        )
        self._metadata_cache[str(source_path)] = metadata

        return destinations

    def create_test_file(
        self,
        name: str,
        description: str,
        test_dir: str | Path = "tests",
        number: Optional[int] = None
    ) -> TestFile:
        """
        Create a new test file with sequential numbering.

        Args:
            name: Test name (e.g., "basic_structure")
            description: Test description
            test_dir: Directory for test files
            number: Specific test number (auto-assigns if None)

        Returns:
            TestFile object with path info
        """
        test_dir = Path(test_dir)
        test_dir.mkdir(parents=True, exist_ok=True)

        if number is None:
            # Use the higher of: internal counter or filesystem-based detection
            fs_number = self._get_next_test_number_from_fs(test_dir)
            number = max(self._next_test_number, fs_number)

        test_file = TestFileInfo(
            number=number,
            name=name,
            description=description,
            path=test_dir / f"test_{number:03d}_{name}.py"
        )

        self._next_test_number = number + 1

        return test_file

    def _get_next_test_number_from_fs(self, test_dir: Path) -> int:
        """
        Get the next available test number based on filesystem.

        Args:
            test_dir: Directory containing test files

        Returns:
            Next available test number
        """
        existing_numbers = []

        if test_dir.exists():
            for f in test_dir.glob("test_*.py"):
                # Extract number from filename like "test_001_something.py"
                parts = f.stem.split("_")
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        existing_numbers.append(num)
                    except ValueError:
                        pass

        if existing_numbers:
            return max(existing_numbers) + 1
        return 1

    def _get_next_test_number(self, test_dir: Path) -> int:
        """
        Get the next available test number (alias for backwards compatibility).

        Args:
            test_dir: Directory containing test files

        Returns:
            Next available test number
        """
        return self._get_next_test_number_from_fs(test_dir)

    def list_test_files(self, test_dir: str | Path = "tests") -> list[TestFile]:
        """
        List all test files with their numbers.

        Args:
            test_dir: Directory containing test files

        Returns:
            List of TestFile objects
        """
        test_dir = Path(test_dir)
        test_files = []

        if not test_dir.exists():
            return test_files

        for f in sorted(test_dir.glob("test_*.py")):
            parts = f.stem.split("_", 2)  # Split into max 3 parts
            if len(parts) >= 3:
                try:
                    number = int(parts[1])
                    name = parts[2]
                    test_files.append(TestFileInfo(
                        number=number,
                        name=name,
                        description="",  # Would need to read file for description
                        path=f
                    ))
                except ValueError:
                    pass

        return test_files

    def save_metadata(self, path: str | Path = "metadata.json") -> None:
        """
        Save all file metadata to JSON.

        Args:
            path: Path to save metadata file
        """
        data = {k: v.to_dict() for k, v in self._metadata_cache.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_metadata(self, path: str | Path = "metadata.json") -> None:
        """
        Load file metadata from JSON.

        Args:
            path: Path to metadata file
        """
        path = Path(path)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            self._metadata_cache = {
                k: FileMetadata(**v) for k, v in data.items()
            }

    def get_category_stats(self) -> dict:
        """
        Get statistics about files in each category.

        Returns:
            Dictionary with counts per category
        """
        stats = {
            "by_tempo": {},
            "by_genre": {},
            "by_mood": {},
            "by_source": {}
        }

        # Count files in each directory
        for tempo in TempoCategory:
            dir_path = self.base_path / "by_tempo" / tempo.value
            if dir_path.exists():
                stats["by_tempo"][tempo.value] = len(list(dir_path.glob("*")))
            else:
                stats["by_tempo"][tempo.value] = 0

        for genre in GenreCategory:
            dir_path = self.base_path / "by_genre" / genre.value
            if dir_path.exists():
                stats["by_genre"][genre.value] = len(list(dir_path.glob("*")))
            else:
                stats["by_genre"][genre.value] = 0

        for mood in MoodCategory:
            dir_path = self.base_path / "by_mood" / mood.value
            if dir_path.exists():
                stats["by_mood"][mood.value] = len(list(dir_path.glob("*")))
            else:
                stats["by_mood"][mood.value] = 0

        for source in SourceCategory:
            dir_path = self.base_path / "by_source" / source.value
            if dir_path.exists():
                stats["by_source"][source.value] = len(list(dir_path.glob("*")))
            else:
                stats["by_source"][source.value] = 0

        return stats


def setup_test_structure(tests_dir: str | Path = "tests") -> list[TestFile]:
    """
    Set up the standard test file structure with numbered tests.

    Args:
        tests_dir: Base directory for tests

    Returns:
        List of created TestFile objects
    """
    tests_dir = Path(tests_dir)
    tests_dir.mkdir(parents=True, exist_ok=True)

    organizer = MusicOrganizer()

    test_definitions = [
        ("directory_structure", "Test that directory structure is created correctly"),
        ("categorization_logic", "Test tempo, genre, mood, and source categorization"),
        ("file_operations", "Test file copying, moving, and duplicate handling"),
        ("tempo_detection", "Test integration with analyzer for tempo detection"),
        ("integration", "Full integration tests with the pipeline"),
    ]

    created_tests = []
    for name, description in test_definitions:
        test_file = organizer.create_test_file(
            name=name,
            description=description,
            test_dir=tests_dir
        )
        created_tests.append(test_file)

    return created_tests


if __name__ == "__main__":
    # Demo usage
    print("Setting up music organizer...")

    organizer = MusicOrganizer(base_path="demo_library")
    dirs = organizer.setup_directories()
    print(f"Created {len(dirs)} directories")

    # Test categorization
    print("\nTempo categorization:")
    print(f"  60 BPM -> {organizer.categorize_by_tempo(60)}")
    print(f"  90 BPM -> {organizer.categorize_by_tempo(90)}")
    print(f"  140 BPM -> {organizer.categorize_by_tempo(140)}")

    print("\nGenre categorization:")
    print(f"  'ambient' -> {organizer.categorize_by_genre('ambient')}")
    print(f"  'piano' -> {organizer.categorize_by_genre('piano')}")

    # Show stats
    stats = organizer.get_category_stats()
    print(f"\nCategory stats: {json.dumps(stats, indent=2)}")
