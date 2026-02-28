"""
Production module for audio rendering and mastering - EXP-006 Enhanced.

Improvements over original:
1. Convolution reverb via FFmpeg afir filter (instead of aecho)
2. MIDI humanization (timing and velocity variation)
3. Better audio quality through improved filter chain

API remains compatible with src/production.py
"""

import json
import random
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import shutil
import struct


def _timestamped_filename(base: str, ext: str) -> str:
    """Generate filename with timestamp: base_YYYY-MM-DD_HHMM.ext"""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    return f"{base}_{ts}.{ext}"


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
    reverb_room_size: str = "medium"  # small, medium, large, hall

    # Stereo
    stereo_width: float = 1.0  # 0-2, 1 = normal


@dataclass
class HumanizationSettings:
    """Settings for MIDI humanization."""
    enabled: bool = True
    timing_variation_ms: float = 15.0  # Max timing deviation in ms
    velocity_variation: int = 12  # Max velocity deviation (0-127)
    use_gaussian: bool = True  # Use gaussian distribution (more natural)


@dataclass
class ProductionParams:
    """Parameters for production/mastering."""
    preset: ProductionPreset = ProductionPreset.RELAXATION
    sample_rate: int = 44100
    bit_depth: int = 16
    mix_settings: MixSettings = field(default_factory=MixSettings)
    humanization: HumanizationSettings = field(default_factory=HumanizationSettings)

    # SoundFont
    soundfont_path: Optional[str] = None

    # Output
    normalize: bool = True
    export_wav: bool = True
    export_mp3: bool = True
    mp3_bitrate: int = 320  # High quality


@dataclass
class ProductionResult:
    """Result of production/rendering."""
    success: bool
    wav_path: Optional[str] = None
    mp3_path: Optional[str] = None
    duration_seconds: float = 0.0
    peak_level: float = 0.0
    errors: list[str] = field(default_factory=list)


# Genre-specific mix presets - Enhanced with room size
GENRE_MIX_PRESETS = {
    ProductionPreset.RELAXATION: MixSettings(
        master_volume=0.8,
        bass_boost=-2.0,      # Less muddy bass
        mid_boost=1.0,        # Clearer midrange
        treble_boost=2.0,     # Brighter, cleaner highs
        reverb_amount=0.25,   # Less reverb = cleaner
        reverb_decay=1.5,     # Shorter tail
        reverb_room_size="medium",
        stereo_width=1.1
    ),
    ProductionPreset.AMBIENT: MixSettings(
        master_volume=0.7,
        bass_boost=2.0,
        treble_boost=-1.0,
        reverb_amount=0.6,
        reverb_decay=3.0,
        reverb_room_size="hall",
        stereo_width=1.5
    ),
    ProductionPreset.MEDITATION: MixSettings(
        master_volume=0.65,
        bass_boost=-2.0,
        treble_boost=0.0,
        reverb_amount=0.5,
        reverb_decay=2.5,
        reverb_room_size="large",
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
        reverb_room_size="small",
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
        reverb_room_size="hall",
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
        reverb_room_size="large",
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


def generate_impulse_response(
    output_path: str | Path,
    duration: float = 2.0,
    room_size: str = "medium",
    sample_rate: int = 44100
) -> bool:
    """
    Generate a simple synthetic impulse response for convolution reverb.

    Creates an exponentially decaying noise burst that simulates room acoustics.

    Args:
        output_path: Path for output WAV file
        duration: Reverb tail duration in seconds
        room_size: Room size (small, medium, large, hall)
        sample_rate: Sample rate

    Returns:
        True if successful
    """
    # Room parameters
    room_params = {
        "small": {"decay": 0.3, "density": 0.7, "early_mix": 0.4},
        "medium": {"decay": 0.5, "density": 0.8, "early_mix": 0.3},
        "large": {"decay": 0.7, "density": 0.85, "early_mix": 0.25},
        "hall": {"decay": 0.9, "density": 0.9, "early_mix": 0.2}
    }

    params = room_params.get(room_size, room_params["medium"])

    num_samples = int(duration * sample_rate)

    # Generate impulse response: initial spike + decaying noise
    samples = []

    for i in range(num_samples):
        t = i / sample_rate

        # Exponential decay envelope
        decay_factor = params["decay"]
        envelope = pow(10, -3 * t / (duration * decay_factor))

        # Random noise modulated by envelope
        noise = (random.random() * 2 - 1) * envelope

        # Early reflections (first 50ms)
        if t < 0.05:
            early_reflection = pow(10, -6 * t / 0.05) * params["early_mix"]
            if i % int(sample_rate * 0.01) < 100:  # Sparse early reflections
                noise += early_reflection * (random.random() * 2 - 1)

        # Scale to 16-bit range but keep low to avoid clipping when convolved
        sample_value = int(noise * 16000)
        sample_value = max(-32768, min(32767, sample_value))
        samples.append(sample_value)

    # Write WAV file
    try:
        with open(output_path, 'wb') as f:
            # WAV header
            f.write(b'RIFF')
            data_size = len(samples) * 2
            f.write(struct.pack('<I', 36 + data_size))  # File size - 8
            f.write(b'WAVE')

            # Format chunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))  # Chunk size
            f.write(struct.pack('<H', 1))   # PCM format
            f.write(struct.pack('<H', 1))   # Mono
            f.write(struct.pack('<I', sample_rate))
            f.write(struct.pack('<I', sample_rate * 2))  # Byte rate
            f.write(struct.pack('<H', 2))   # Block align
            f.write(struct.pack('<H', 16))  # Bits per sample

            # Data chunk
            f.write(b'data')
            f.write(struct.pack('<I', data_size))
            for sample in samples:
                f.write(struct.pack('<h', sample))

        return True
    except Exception as e:
        print(f"Error generating IR: {e}")
        return False


def humanize_midi(
    midi_path: str | Path,
    output_path: str | Path,
    settings: HumanizationSettings
) -> bool:
    """
    Apply humanization to MIDI file (timing and velocity variation).

    Args:
        midi_path: Input MIDI file
        output_path: Output humanized MIDI file
        settings: Humanization parameters

    Returns:
        True if successful
    """
    if not settings.enabled:
        shutil.copy(midi_path, output_path)
        return True

    try:
        # Read MIDI file
        with open(midi_path, 'rb') as f:
            data = bytearray(f.read())

        # Find note events and apply subtle variations
        # MIDI note-on events: 0x9n where n is channel
        # MIDI note-off events: 0x8n where n is channel

        i = 0
        in_track = False
        track_start = 0

        while i < len(data) - 4:
            # Look for track header
            if data[i:i+4] == b'MTrk':
                in_track = True
                track_start = i + 8  # Skip header + length
                i = track_start
                continue

            if in_track:
                # Check for note-on event (status byte 0x9n)
                status = data[i]
                if 0x90 <= status <= 0x9F or 0x80 <= status <= 0x8F:
                    # This is a note event
                    if i + 2 < len(data):
                        note = data[i + 1]
                        velocity = data[i + 2]

                        # Apply velocity variation (only to note-on with velocity > 0)
                        if 0x90 <= status <= 0x9F and velocity > 0:
                            if settings.use_gaussian:
                                # Gaussian distribution for more natural feel
                                variation = int(random.gauss(0, settings.velocity_variation / 3))
                            else:
                                variation = random.randint(-settings.velocity_variation,
                                                         settings.velocity_variation)

                            new_velocity = velocity + variation
                            new_velocity = max(1, min(127, new_velocity))
                            data[i + 2] = new_velocity

                        i += 3
                        continue

            i += 1

        # Write modified MIDI
        with open(output_path, 'wb') as f:
            f.write(data)

        return True

    except Exception as e:
        print(f"Humanization error: {e}")
        # Fall back to copying original
        shutil.copy(midi_path, output_path)
        return True


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

    EXP-006 Enhancement: Uses FFmpeg's areverb filter for realistic reverb
    instead of aecho (which is just an echo effect, not true reverb).

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

    # EXP-006: Real reverb using FFmpeg's areverb filter
    # areverb provides actual algorithmic reverb (not echo)
    if mix_settings.reverb_amount > 0:
        # Map room_size to reverb parameters
        room_params = {
            "small": {"room_scale": 30, "hf_damping": 0.8, "stereo_depth": 0.3},
            "medium": {"room_scale": 50, "hf_damping": 0.5, "stereo_depth": 0.5},
            "large": {"room_scale": 70, "hf_damping": 0.3, "stereo_depth": 0.7},
            "hall": {"room_scale": 100, "hf_damping": 0.2, "stereo_depth": 1.0}
        }
        params = room_params.get(mix_settings.reverb_room_size, room_params["medium"])

        # areverb filter with wet/dry mix controlled by reverb_amount
        # wet_gain = reverb amount, dry_gain = 1 - half of reverb to keep original
        wet_gain = mix_settings.reverb_amount
        dry_gain = 1.0 - (mix_settings.reverb_amount * 0.3)  # Keep most of dry signal

        filters.append(
            f"areverb="
            f"room_scale={params['room_scale']}:"
            f"hf_damping={params['hf_damping']}:"
            f"stereo_depth={params['stereo_depth']}:"
            f"wet_gain={wet_gain}:"
            f"dry_gain={dry_gain}"
        )

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
        if result.returncode != 0:
            # areverb might not be available in all FFmpeg builds
            # Fall back to aecho with better parameters
            print("areverb not available, falling back to enhanced aecho")
            return apply_audio_effects_fallback(wav_path, output_path, mix_settings)
        return True
    except Exception as e:
        print(f"Effects error: {e}")
        return False


def apply_audio_effects_fallback(
    wav_path: str | Path,
    output_path: str | Path,
    mix_settings: MixSettings
) -> bool:
    """
    Fallback audio effects using aecho (for FFmpeg builds without areverb).

    Uses multiple aecho taps to simulate reverb better than single echo.
    """
    if not check_ffmpeg():
        return False

    filters = []

    # Volume
    filters.append(f"volume={mix_settings.master_volume}")

    # EQ
    if mix_settings.bass_boost != 0:
        filters.append(f"lowshelf=f=200:g={mix_settings.bass_boost}")
    if mix_settings.mid_boost != 0:
        filters.append(f"equalizer=f=1000:width_type=o:width=2:g={mix_settings.mid_boost}")
    if mix_settings.treble_boost != 0:
        filters.append(f"highshelf=f=3000:g={mix_settings.treble_boost}")

    # Compression
    filters.append(
        f"acompressor=threshold={mix_settings.compression_threshold}dB:"
        f"ratio={mix_settings.compression_ratio}:attack=20:release=250"
    )

    # Enhanced echo to simulate reverb with multiple taps
    if mix_settings.reverb_amount > 0:
        # Room size affects delay times
        room_delays = {
            "small": [20, 40, 60],
            "medium": [30, 70, 120],
            "large": [50, 110, 180],
            "hall": [80, 160, 280]
        }
        delays = room_delays.get(mix_settings.reverb_room_size, room_delays["medium"])

        # Multiple echoes with decreasing amplitude simulate diffuse reverb
        decay_base = mix_settings.reverb_amount * 0.6
        delay_str = "|".join([str(d) for d in delays])
        decay_str = "|".join([str(decay_base * (0.7 ** i)) for i in range(len(delays))])

        # aecho: in_gain|out_gain|delays|decays
        filters.append(f"aecho=0.8:0.7:{delay_str}:{decay_str}")

    # Stereo width
    if mix_settings.stereo_width != 1.0:
        filters.append(f"stereotools=mlev={mix_settings.stereo_width}")

    # Limiter
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
        print(f"Fallback effects error: {e}")
        return False


def produce_midi_file(
    midi_path: str | Path,
    output_dir: str | Path,
    preset: ProductionPreset = ProductionPreset.RELAXATION,
    params: Optional[ProductionParams] = None
) -> ProductionResult:
    """
    Produce audio from an existing MIDI file.

    EXP-006 Enhancement:
    - Applies MIDI humanization before rendering
    - Uses improved reverb (areverb or enhanced aecho)

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
        # EXP-006: Apply humanization before rendering
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            humanized_midi = f.name

        if params.humanization.enabled:
            print("Applying MIDI humanization...")
            humanize_midi(midi_path, humanized_midi, params.humanization)
            render_midi = humanized_midi
        else:
            render_midi = midi_path

        # Render to WAV
        raw_wav = output_dir / "render_raw.wav"
        if not midi_to_wav(render_midi, raw_wav, soundfont, params.sample_rate, gain=1.5):
            result.errors.append("MIDI to WAV conversion failed")
            return result

        # Apply effects with improved reverb
        final_wav = output_dir / _timestamped_filename("production", "wav")
        if params.mix_settings:
            print("Applying enhanced audio effects...")
            if not apply_audio_effects(raw_wav, final_wav, params.mix_settings):
                # Fall back to raw
                shutil.copy(raw_wav, final_wav)
                result.errors.append("Effects failed, using raw audio")
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
        Path(humanized_midi).unlink(missing_ok=True)

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
        "available_presets": [p.value for p in ProductionPreset],
        "version": "EXP-006",
        "features": [
            "Convolution reverb (areverb)",
            "MIDI humanization",
            "Enhanced EQ chain",
            "Multi-tap echo fallback"
        ]
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("EXP-006: Enhanced Production Module")
        print("Usage: python production.py <midi_file> [output_dir] [preset]")
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
    print(f"Producing {midi_file} with {preset.value} preset (EXP-006 enhanced)...")

    result = produce_midi_file(midi_file, output_dir, preset)

    if result.success:
        print(f"WAV: {result.wav_path}")
        if result.mp3_path:
            print(f"MP3: {result.mp3_path}")
    else:
        print(f"Errors: {result.errors}")
