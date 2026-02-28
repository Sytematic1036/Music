"""
EXP-006: Realistic Audio Quality

Enhanced production module with:
- Convolution reverb (areverb filter)
- MIDI humanization (timing/velocity variation)
- Server-side rendering in GUI
"""

from .production import (
    ProductionPreset,
    MixSettings,
    HumanizationSettings,
    ProductionParams,
    ProductionResult,
    GENRE_MIX_PRESETS,
    find_soundfont,
    check_fluidsynth,
    check_ffmpeg,
    midi_to_wav,
    wav_to_mp3,
    apply_audio_effects,
    humanize_midi,
    produce_midi_file,
    get_production_info,
)

__version__ = "0.1.0"
__all__ = [
    "ProductionPreset",
    "MixSettings",
    "HumanizationSettings",
    "ProductionParams",
    "ProductionResult",
    "GENRE_MIX_PRESETS",
    "find_soundfont",
    "check_fluidsynth",
    "check_ffmpeg",
    "midi_to_wav",
    "wav_to_mp3",
    "apply_audio_effects",
    "humanize_midi",
    "produce_midi_file",
    "get_production_info",
]
