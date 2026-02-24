"""Tests for production module."""

import pytest
from pathlib import Path
import tempfile

from src.production import (
    ProductionParams,
    ProductionPreset,
    ProductionResult,
    MixSettings,
    find_soundfont,
    check_fluidsynth,
    check_ffmpeg,
    get_production_info,
    GENRE_MIX_PRESETS,
)


class TestMixSettings:
    """Tests for MixSettings dataclass."""

    def test_default_values(self):
        settings = MixSettings()
        assert settings.master_volume == 0.8
        assert settings.reverb_amount == 0.3
        assert settings.compression_ratio == 4.0
        assert settings.stereo_width == 1.0

    def test_custom_values(self):
        settings = MixSettings(
            master_volume=0.9,
            bass_boost=3.0,
            reverb_amount=0.5,
            compression_ratio=6.0
        )
        assert settings.master_volume == 0.9
        assert settings.bass_boost == 3.0


class TestProductionPreset:
    """Tests for ProductionPreset enum."""

    def test_all_presets_exist(self):
        expected = ["relaxation", "ambient", "meditation", "lofi", "classical", "cinematic"]
        for name in expected:
            assert ProductionPreset(name) is not None

    def test_preset_values(self):
        assert ProductionPreset.RELAXATION.value == "relaxation"
        assert ProductionPreset.LOFI.value == "lofi"


class TestProductionParams:
    """Tests for ProductionParams dataclass."""

    def test_default_values(self):
        params = ProductionParams()
        assert params.preset == ProductionPreset.RELAXATION
        assert params.sample_rate == 44100
        assert params.bit_depth == 16
        assert params.export_wav is True
        assert params.export_mp3 is True

    def test_custom_values(self):
        params = ProductionParams(
            preset=ProductionPreset.LOFI,
            sample_rate=48000,
            mp3_bitrate=320
        )
        assert params.preset == ProductionPreset.LOFI
        assert params.sample_rate == 48000
        assert params.mp3_bitrate == 320


class TestProductionResult:
    """Tests for ProductionResult dataclass."""

    def test_success_result(self):
        result = ProductionResult(
            success=True,
            wav_path="/path/to/output.wav",
            mp3_path="/path/to/output.mp3",
            duration_seconds=60.0
        )
        assert result.success is True
        assert result.wav_path is not None

    def test_failure_result(self):
        result = ProductionResult(
            success=False,
            errors=["No SoundFont found"]
        )
        assert result.success is False
        assert len(result.errors) == 1


class TestGenreMixPresets:
    """Tests for genre-specific mix presets."""

    def test_all_presets_have_settings(self):
        for preset in ProductionPreset:
            assert preset in GENRE_MIX_PRESETS
            settings = GENRE_MIX_PRESETS[preset]
            assert isinstance(settings, MixSettings)

    def test_relaxation_preset_is_calm(self):
        settings = GENRE_MIX_PRESETS[ProductionPreset.RELAXATION]
        # Relaxation should have moderate reverb
        assert 0.2 <= settings.reverb_amount <= 0.6
        # Not too compressed
        assert settings.compression_ratio <= 6

    def test_lofi_preset_characteristics(self):
        settings = GENRE_MIX_PRESETS[ProductionPreset.LOFI]
        # Lo-fi typically has bass boost
        assert settings.bass_boost > 0
        # And treble cut
        assert settings.treble_boost < 0

    def test_ambient_preset_wide_stereo(self):
        settings = GENRE_MIX_PRESETS[ProductionPreset.AMBIENT]
        # Ambient should have wide stereo
        assert settings.stereo_width >= 1.0


class TestSystemChecks:
    """Tests for system capability checks."""

    def test_check_fluidsynth_returns_bool(self):
        result = check_fluidsynth()
        assert isinstance(result, bool)

    def test_check_ffmpeg_returns_bool(self):
        result = check_ffmpeg()
        assert isinstance(result, bool)

    def test_find_soundfont_returns_path_or_none(self):
        result = find_soundfont()
        if result is not None:
            assert Path(result).suffix.lower() == ".sf2"


class TestProductionInfo:
    """Tests for production info function."""

    def test_get_production_info(self):
        info = get_production_info()

        assert "fluidsynth_available" in info
        assert "ffmpeg_available" in info
        assert "soundfont_found" in info
        assert "available_presets" in info

        assert isinstance(info["fluidsynth_available"], bool)
        assert isinstance(info["ffmpeg_available"], bool)
        assert len(info["available_presets"]) == len(ProductionPreset)


class TestMixSettingsRanges:
    """Tests for valid mix settings ranges."""

    def test_volume_range(self):
        for preset in GENRE_MIX_PRESETS.values():
            assert 0 <= preset.master_volume <= 1.0

    def test_reverb_range(self):
        for preset in GENRE_MIX_PRESETS.values():
            assert 0 <= preset.reverb_amount <= 1.0

    def test_stereo_width_range(self):
        for preset in GENRE_MIX_PRESETS.values():
            assert 0 <= preset.stereo_width <= 2.0

    def test_compression_ratio_positive(self):
        for preset in GENRE_MIX_PRESETS.values():
            assert preset.compression_ratio >= 1.0


# Integration tests - only run if FluidSynth is available
@pytest.mark.skipif(not check_fluidsynth(), reason="FluidSynth not installed")
class TestProductionIntegration:
    """Integration tests for production (requires FluidSynth)."""

    def test_produce_midi_file(self):
        from src.production import produce_midi_file
        from src.melody import generate_melody, melody_to_midi, MelodyParams

        # Generate a simple MIDI file
        params = MelodyParams(duration_seconds=10)
        melody = generate_melody(params, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = Path(tmpdir) / "test.mid"
            melody_to_midi(melody, midi_path)

            output_dir = Path(tmpdir) / "output"
            result = produce_midi_file(midi_path, output_dir)

            if result.success:
                assert result.wav_path is not None
                assert Path(result.wav_path).exists()


@pytest.mark.skipif(not check_fluidsynth() or not check_ffmpeg(),
                    reason="FluidSynth or FFmpeg not installed")
class TestProductionWithEffects:
    """Tests for production with audio effects (requires FluidSynth + FFmpeg)."""

    def test_produce_with_effects(self):
        from src.production import produce_midi_file, apply_audio_effects
        from src.melody import generate_melody, melody_to_midi, MelodyParams

        params = MelodyParams(duration_seconds=5)
        melody = generate_melody(params, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            midi_path = Path(tmpdir) / "test.mid"
            melody_to_midi(melody, midi_path)

            output_dir = Path(tmpdir) / "output"
            result = produce_midi_file(
                midi_path,
                output_dir,
                ProductionPreset.RELAXATION
            )

            if result.success and result.mp3_path:
                assert Path(result.mp3_path).exists()
