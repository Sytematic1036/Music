"""
Music Generation System

Complete pipeline for music creation:
1. Melody - Generate and optimize unique melodies
2. Arrangement - Multi-track instrument layering
3. Production - Mix, master, and export audio

Plus:
- Learning system with vector database
- Multiple playback methods (browser, python, export)
"""

__version__ = "0.2.0"

# Core modules (EXP-001)
from .youtube_search import search_relaxation_music
from .downloader import download_audio
from .analyzer import analyze_audio, analyze_for_generation
from .generator import generate_relaxation_midi, GenerationParams

# Extended modules (EXP-003)
from .melody import (
    Melody,
    MelodyParams,
    generate_melody,
    generate_melody_for_genre,
    melody_to_midi,
    Contour,
    GENRE_PRESETS as MELODY_PRESETS
)
from .arrangement import (
    Arrangement,
    ArrangementParams,
    arrange_melody,
    arrangement_to_midi,
    Instrument,
    TrackRole
)
from .production import (
    ProductionParams,
    ProductionPreset,
    produce_arrangement,
    produce_midi_file,
    MixSettings
)
from .player import (
    PlaybackMethod,
    play,
    play_with_browser,
    create_browser_player
)
from .learning import (
    LearningDatabase,
    GenerationRecord,
    create_record_from_generation
)
from .music_pipeline import (
    MusicPipeline,
    PipelineResult,
    create_quick_track
)
