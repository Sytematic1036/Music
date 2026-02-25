"""
Production module for audio rendering and mastering.

Implements best practices for music production:
- MIDI to audio conversion via FluidSynth
- Genre-specific mixing presets
- Basic mastering (compression, EQ, limiting)
- Export to WAV and MP3
"""

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import shutil

from .arrangement import Arrangement, arrangement_to_midi


class ProductionPreset(Enum):
    """Production presets for different genres."""
    RELAXATION = "relaxation"
    AMBIENT = "ambient"
    MEDITATION = "meditation"
    LOFI = "lofi"
    CLASSICAL = "classical"
    CINEMATIC = "cinematic"


@dataclass
class MixSettings:
    """Mixing settings for production."""
    # Levels (0-1)
    master_volume: float = 0.8

    # EQ (decibels)
    bass_boost: float = 0.0
    mid_boost: float = 0.0
    treble_boost: float = 0.0

    # Compression
    compression_threshold: float = -12.0  # dB
    compression_ratio: float = 4.0

    # Reverb (0-1)
    reverb_amount: float = 0.3
    reverb_decay: float = 1.5  # seconds

    # Stereo
    stereo_width: float = 1.0  # 0-2, 1 = normal


@dataclass
class ProductionParams:
    """Parameters for production/mastering."""
    preset: ProductionPreset = ProductionPreset.RELAXATION
    sample_rate: int = 44100
    bit_depth: int = 16
    mix_settings: MixSettings = field(default_factory=MixSettings)

    # SoundFont
    soundfont_path: Optional[str] = None

    # Output
    normalize: bool = True
    export_wav: bool = True
    export_mp3: bool = True
    mp3_bitrate: int = 192


@dataclass
class ProductionResult:
    """Result of production/rendering."""
    success: bool
    wav_path: Optional[str] = None
    mp3_path: Optional[str] = None
    duration_seconds: float = 0.0
    peak_level: float = 0.0
    errors: list[str] = field(default_factory=list)


# Genre-specific mix presets
GENRE_MIX_PRESETS = {
    ProductionPreset.RELAXATION: MixSettings(
        master_volume=0.75,
        bass_boost=-1.0,
        treble_boost=1.0,
        reverb_amount=0.4,
        reverb_decay=2.0,
        stereo_width=1.2
    ),
    ProductionPreset.AMBIENT: MixSettings(
        master_volume=0.7,
        bass_boost=2.0,
        treble_boost=-1.0,
        reverb_amount=0.6,
        reverb_decay=3.0,
        stereo_width=1.5
    ),
    ProductionPreset.MEDITATION: MixSettings(
        master_volume=0.65,
        bass_boost=-2.0,
        treble_boost=0.0,
        reverb_amount=0.5,
        reverb_decay=2.5,
        stereo_width=1.3
    ),
    ProductionPreset.LOFI: MixSettings(
        master_volume=0.8,
        bass_boost=3.0,
        mid_boost=-2.0,
        treble_boost=-3.0,
        compression_threshold=-8.0,
        compression_ratio=6.0,
        reverb_amount=0.2,
        stereo_width=0.9
    ),
    ProductionPreset.CLASSICAL: MixSettings(
        master_volume=0.85,
        bass_boost=0.0,
        mid_boost=1.0,
        treble_boost=0.5,
        compression_ratio=2.0,
        reverb_amount=0.35,
        reverb_decay=1.8,
        stereo_width=1.1
    ),
    ProductionPreset.CINEMATIC: MixSettings(
        master_volume=0.9,
        bass_boost=4.0,
        treble_boost=2.0,
        compression_threshold=-6.0,
        compression_ratio=4.0,
        reverb_amount=0.45,
        reverb_decay=2.2,
        stereo_width=1.4
    )
}


def find_soundfont() -> Optional[str]:
    """
    Find a SoundFont file on the system.

    Looks in common locations for FluidR3_GM or similar.
    """
    common_paths = [
        # Windows
        "C:/soundfonts/FluidR3_GM.sf2",
        "C:/soundfonts/default.sf2",
        Path.home() / "soundfonts" / "FluidR3_GM.sf2",
        Path.home() / "soundfonts" / "default.sf2",

        # Linux
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/FluidR3_GM.sf2",
        "/usr/share/sounds/sf2/default.sf2",

        # macOS
        "/usr/local/share/fluidsynth/FluidR3_GM.sf2",
        Path.home() / "Library" / "Audio" / "Sounds" / "Banks" / "FluidR3_GM.sf2",
    ]

    for path in common_paths:
        path = Path(path)
        if path.exists():
            return str(path)

    return None


def download_soundfont(output_dir: str | Path = None) -> Optional[str]:
    """
    Download a free SoundFont if none found.

    Uses FluidR3_GM from a free source.
    """
    if output_dir is None:
        output_dir = Path.home() / "soundfonts"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "FluidR3_GM.sf2"

    if output_path.exists():
        return str(output_path)

    # FluidR3_GM is large (~140MB), try smaller alternative first
    # GeneralUser GS is smaller and good quality
    urls = [
        # Smaller option (~30MB)
        "https://archive.org/download/GeneralUserGS/GeneralUser_GS_1.471.sf2",
    ]

    for url in urls:
        try:
            print(f"Downloading SoundFont from {url}...")
            result = subprocess.run(
                ["curl", "-L", "-o", str(output_path), url],
                capture_output=True,
                timeout=300
            )
            if result.returncode == 0 and output_path.exists():
                print(f"Downloaded to: {output_path}")
                return str(output_path)
        except Exception as e:
            print(f"Download failed: {e}")
            continue

    return None


def check_fluidsynth() -> bool:
    """Check if FluidSynth is installed."""
    try:
        # FluidSynth doesn't support --version, use -h instead
        result = subprocess.run(
            ["fluidsynth", "-h"],
            capture_output=True,
            timeout=5
        )
        # -h returns 1 but outputs help text
        return b"Usage:" in result.stdout or b"Usage:" in result.stderr
    except Exception:
        return False


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def midi_to_wav(
    midi_path: str | Path,
    output_path: str | Path,
    soundfont_path: str,
    sample_rate: int = 44100,
    gain: float = 1.0
) -> bool:
    """
    Convert MIDI to WAV using FluidSynth.

    Args:
        midi_path: Path to MIDI file
        output_path: Path for output WAV
        soundfont_path: Path to SoundFont (.sf2)
        sample_rate: Output sample rate
        gain: Volume gain (0.1 - 10.0)

    Returns:
        True if successful
    """
    if not check_fluidsynth():
        raise RuntimeError("FluidSynth not found. Install with: choco install fluidsynth")

    cmd = [
        "fluidsynth",
        "-ni",  # No interactive mode
        "-F", str(output_path),  # Output file
        "-r", str(sample_rate),  # Sample rate
        "-g", str(gain),  # Gain
        str(soundfont_path),  # SoundFont
        str(midi_path)  # MIDI file
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"FluidSynth error: {e}")
        return False


def wav_to_mp3(
    wav_path: str | Path,
    output_path: str | Path,
    bitrate: int = 192
) -> bool:
    """
    Convert WAV to MP3 using FFmpeg.

    Args:
        wav_path: Path to WAV file
        output_path: Path for output MP3
        bitrate: MP3 bitrate in kbps

    Returns:
        True if successful
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg not found. Install with: choco install ffmpeg")

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-b:a", f"{bitrate}k",
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"FFmpeg error: {e}")
        return False


def apply_audio_effects(
    wav_path: str | Path,
    output_path: str | Path,
    mix_settings: MixSettings
) -> bool:
    """
    Apply audio effects using FFmpeg filters.

    Best practice: Gentle processing for music - don't over-compress.
    """
    if not check_ffmpeg():
        return False

    filters = []

    # Volume
    filters.append(f"volume={mix_settings.master_volume}")

    # EQ (using lowshelf, peak, highshelf)
    if mix_settings.bass_boost != 0:
        filters.append(f"lowshelf=f=200:g={mix_settings.bass_boost}")
    if mix_settings.mid_boost != 0:
        filters.append(f"equalizer=f=1000:width_type=o:width=2:g={mix_settings.mid_boost}")
    if mix_settings.treble_boost != 0:
        filters.append(f"highshelf=f=3000:g={mix_settings.treble_boost}")

    # Compression (using acompressor)
    filters.append(
        f"acompressor=threshold={mix_settings.compression_threshold}dB:"
        f"ratio={mix_settings.compression_ratio}:attack=20:release=250"
    )

    # Reverb using aecho (simple reverb approximation)
    if mix_settings.reverb_amount > 0:
        delay = int(mix_settings.reverb_decay * 100)
        decay = mix_settings.reverb_amount
        filters.append(f"aecho=0.8:0.9:{delay}:{decay}")

    # Stereo width using stereotools
    if mix_settings.stereo_width != 1.0:
        filters.append(f"stereotools=mlev={mix_settings.stereo_width}")

    # Limiter to prevent clipping
    filters.append("alimiter=limit=0.95:attack=5:release=50")

    filter_string = ",".join(filters)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(wav_path),
        "-af", filter_string,
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Effects error: {e}")
        return False


def produce_arrangement(
    arrangement: Arrangement,
    output_dir: str | Path,
    params: Optional[ProductionParams] = None
) -> ProductionResult:
    """
    Produce (render) an arrangement to audio files.

    Args:
        arrangement: Arrangement to produce
        output_dir: Directory for output files
        params: Production parameters

    Returns:
        ProductionResult with file paths and status
    """
    if params is None:
        # Use genre from arrangement
        genre = arrangement.params.genre
        preset = ProductionPreset(genre) if genre in [p.value for p in ProductionPreset] else ProductionPreset.RELAXATION
        params = ProductionParams(preset=preset)
        params.mix_settings = GENRE_MIX_PRESETS.get(preset, MixSettings())

    result = ProductionResult(success=False)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find or get soundfont
    soundfont = params.soundfont_path or find_soundfont()
    if not soundfont:
        soundfont = download_soundfont()
    if not soundfont:
        result.errors.append("No SoundFont found and download failed")
        return result

    # Create temp MIDI file
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        midi_path = f.name

    try:
        # Export arrangement to MIDI
        arrangement_to_midi(arrangement, midi_path)

        # Render to WAV
        raw_wav = output_dir / "render_raw.wav"
        if not midi_to_wav(midi_path, raw_wav, soundfont, params.sample_rate):
            result.errors.append("MIDI to WAV conversion failed")
            return result

        # Apply effects
        final_wav = output_dir / "production.wav"
        if params.mix_settings:
            if not apply_audio_effects(raw_wav, final_wav, params.mix_settings):
                # Fall back to raw
                shutil.copy(raw_wav, final_wav)
                result.errors.append("Effects failed, using raw audio")
        else:
            shutil.copy(raw_wav, final_wav)

        result.wav_path = str(final_wav)

        # Export to MP3 if requested
        if params.export_mp3:
            mp3_path = output_dir / "production.mp3"
            if wav_to_mp3(final_wav, mp3_path, params.mp3_bitrate):
                result.mp3_path = str(mp3_path)
            else:
                result.errors.append("MP3 export failed")

        # Get duration
        result.duration_seconds = arrangement.get_duration_beats() * 60 / arrangement.params.tempo
        result.success = True

        # Cleanup temp files
        Path(midi_path).unlink(missing_ok=True)
        raw_wav.unlink(missing_ok=True)

    except Exception as e:
        result.errors.append(str(e))

    return result


def produce_midi_file(
    midi_path: str | Path,
    output_dir: str | Path,
    preset: ProductionPreset = ProductionPreset.RELAXATION,
    params: Optional[ProductionParams] = None
) -> ProductionResult:
    """
    Produce audio from an existing MIDI file.

    Args:
        midi_path: Path to MIDI file
        output_dir: Directory for output files
        preset: Production preset
        params: Production parameters

    Returns:
        ProductionResult with file paths and status
    """
    if params is None:
        params = ProductionParams(preset=preset)
        params.mix_settings = GENRE_MIX_PRESETS.get(preset, MixSettings())

    result = ProductionResult(success=False)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find soundfont
    soundfont = params.soundfont_path or find_soundfont()
    if not soundfont:
        soundfont = download_soundfont()
    if not soundfont:
        result.errors.append("No SoundFont found")
        return result

    try:
        # Render to WAV
        raw_wav = output_dir / "render_raw.wav"
        if not midi_to_wav(midi_path, raw_wav, soundfont, params.sample_rate):
            result.errors.append("MIDI to WAV conversion failed")
            return result

        # Apply effects
        final_wav = output_dir / "production.wav"
        if params.mix_settings:
            apply_audio_effects(raw_wav, final_wav, params.mix_settings)
        else:
            shutil.copy(raw_wav, final_wav)

        result.wav_path = str(final_wav)

        # Export to MP3
        if params.export_mp3:
            mp3_path = output_dir / "production.mp3"
            if wav_to_mp3(final_wav, mp3_path, params.mp3_bitrate):
                result.mp3_path = str(mp3_path)

        result.success = True

        # Cleanup
        raw_wav.unlink(missing_ok=True)

    except Exception as e:
        result.errors.append(str(e))

    return result


def get_production_info() -> dict:
    """Get info about production capabilities."""
    return {
        "fluidsynth_available": check_fluidsynth(),
        "ffmpeg_available": check_ffmpeg(),
        "soundfont_found": find_soundfont() is not None,
        "soundfont_path": find_soundfont(),
        "available_presets": [p.value for p in ProductionPreset]
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.production <midi_file> [output_dir] [preset]")
        print("\nAvailable presets:", [p.value for p in ProductionPreset])
        print("\nSystem info:")
        info = get_production_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        sys.exit(1)

    midi_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    preset_name = sys.argv[3] if len(sys.argv) > 3 else "relaxation"

    preset = ProductionPreset(preset_name)
    print(f"Producing {midi_file} with {preset.value} preset...")

    result = produce_midi_file(midi_file, output_dir, preset)

    if result.success:
        print(f"WAV: {result.wav_path}")
        if result.mp3_path:
            print(f"MP3: {result.mp3_path}")
    else:
        print(f"Errors: {result.errors}")
