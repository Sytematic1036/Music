"""
Test 004: Test Numbering

Tests the sequential test file numbering system (test_001_, test_002_, etc.).
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.organizer import MusicOrganizer, TestFile


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def organizer():
    """Create a MusicOrganizer instance."""
    return MusicOrganizer()


class TestTestFileCreation:
    """Tests for test file creation with sequential numbering."""

    def test_create_first_test(self, organizer, temp_dir):
        """Test creating the first test file."""
        test_dir = temp_dir / "tests"

        test_file = organizer.create_test_file(
            name="basic_structure",
            description="Test basic structure",
            test_dir=test_dir
        )

        assert test_file.number == 1
        assert test_file.name == "basic_structure"
        assert test_file.prefix == "test_001"
        assert test_file.full_name == "test_001_basic_structure"

    def test_create_sequential_tests(self, organizer, temp_dir):
        """Test creating multiple sequential test files."""
        test_dir = temp_dir / "tests"

        test1 = organizer.create_test_file("first", "First test", test_dir)
        test2 = organizer.create_test_file("second", "Second test", test_dir)
        test3 = organizer.create_test_file("third", "Third test", test_dir)

        assert test1.number == 1
        assert test2.number == 2
        assert test3.number == 3

    def test_create_with_explicit_number(self, organizer, temp_dir):
        """Test creating a test with explicit number."""
        test_dir = temp_dir / "tests"

        test_file = organizer.create_test_file(
            name="explicit",
            description="Test with explicit number",
            test_dir=test_dir,
            number=42
        )

        assert test_file.number == 42
        assert test_file.prefix == "test_042"

    def test_prefix_format(self, organizer, temp_dir):
        """Test that prefix is zero-padded to 3 digits."""
        test_dir = temp_dir / "tests"

        test1 = organizer.create_test_file("a", "Test", test_dir, number=1)
        test2 = organizer.create_test_file("b", "Test", test_dir, number=10)
        test3 = organizer.create_test_file("c", "Test", test_dir, number=100)

        assert test1.prefix == "test_001"
        assert test2.prefix == "test_010"
        assert test3.prefix == "test_100"


class TestExistingTestDetection:
    """Tests for detecting existing test files."""

    def test_detect_existing_tests(self, organizer, temp_dir):
        """Test that next number accounts for existing tests."""
        test_dir = temp_dir / "tests"
        test_dir.mkdir()

        # Create some existing test files
        (test_dir / "test_001_first.py").write_text("# test")
        (test_dir / "test_002_second.py").write_text("# test")

        # Create new test - should be number 3
        test_file = organizer.create_test_file("third", "Third test", test_dir)

        assert test_file.number == 3

    def test_detect_gap_in_numbers(self, organizer, temp_dir):
        """Test that gaps in numbering don't cause issues."""
        test_dir = temp_dir / "tests"
        test_dir.mkdir()

        # Create tests with a gap
        (test_dir / "test_001_first.py").write_text("# test")
        (test_dir / "test_005_fifth.py").write_text("# test")

        # Next should be 6, not 2
        test_file = organizer.create_test_file("sixth", "Sixth test", test_dir)

        assert test_file.number == 6


class TestListTestFiles:
    """Tests for listing test files."""

    def test_list_empty_directory(self, organizer, temp_dir):
        """Test listing empty test directory."""
        test_dir = temp_dir / "tests"

        test_files = organizer.list_test_files(test_dir)

        assert test_files == []

    def test_list_existing_tests(self, organizer, temp_dir):
        """Test listing existing test files."""
        test_dir = temp_dir / "tests"
        test_dir.mkdir()

        # Create some test files
        (test_dir / "test_001_first.py").write_text("# test")
        (test_dir / "test_002_second.py").write_text("# test")
        (test_dir / "test_003_third.py").write_text("# test")
        # Also create a non-test file
        (test_dir / "conftest.py").write_text("# conftest")

        test_files = organizer.list_test_files(test_dir)

        assert len(test_files) == 3
        assert all(isinstance(tf, TestFile) for tf in test_files)

    def test_list_sorted_by_number(self, organizer, temp_dir):
        """Test that listed tests are sorted by number."""
        test_dir = temp_dir / "tests"
        test_dir.mkdir()

        # Create in random order
        (test_dir / "test_003_third.py").write_text("# test")
        (test_dir / "test_001_first.py").write_text("# test")
        (test_dir / "test_002_second.py").write_text("# test")

        test_files = organizer.list_test_files(test_dir)

        numbers = [tf.number for tf in test_files]
        assert numbers == [1, 2, 3]


class TestTestFilePath:
    """Tests for test file path generation."""

    def test_path_format(self, organizer, temp_dir):
        """Test that path is correctly formatted."""
        test_dir = temp_dir / "tests"

        test_file = organizer.create_test_file(
            name="basic_structure",
            description="Test basic",
            test_dir=test_dir,
            number=1
        )

        expected_path = test_dir / "test_001_basic_structure.py"
        assert test_file.path == expected_path

    def test_full_name_property(self, organizer, temp_dir):
        """Test full_name property."""
        test_dir = temp_dir / "tests"

        test_file = organizer.create_test_file(
            name="categorization_logic",
            description="Test categorization",
            test_dir=test_dir,
            number=2
        )

        assert test_file.full_name == "test_002_categorization_logic"
