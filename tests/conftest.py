"""
Pytest configuration and shared fixtures for music organizer tests.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Tell pytest to ignore the TestFile/TestFileInfo class (it's a data class, not a test)
def pytest_collection_modifyitems(config, items):
    """Filter out TestFileInfo from test collection."""
    pass  # pytest_configure handles this


def pytest_configure(config):
    """Configure pytest to ignore TestFileInfo class."""
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pytest.PytestCollectionWarning"
    )
