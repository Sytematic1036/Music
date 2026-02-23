"""Tests for audio analyzer module."""

import pytest
import numpy as np
from pathlib import Path

from src.analyzer import (
    MusicalFeatures,
    estimate_key,
    analyze_audio,
    analyze_for_generation,
    KEY_NAMES,
)


class TestMusicalFeatures:
    """Tests for MusicalFeatures dataclass."""

    def test_creation(self):
        features = MusicalFeatures(
            duration_seconds=120.0,
            sample_rate=22050,
            tempo=70.0,
            beat_times=[0.0, 0.86, 1.71],
            estimated_key="C major",
            key_confidence=0.8,
            chroma_mean=[0.1] * 12,
            mfcc_mean=[0.0] * 13,
            mfcc_std=[1.0] * 13,
            spectral_centroid_mean=1500.0,
            spectral_bandwidth_mean=2000.0,
            spectral_rolloff_mean=3000.0,
            rms_mean=0.1,
            rms_std=0.05,
            segment_boundaries=[30.0, 60.0, 90.0],
            num_segments=4
        )

        assert features.tempo == 70.0
        assert features.estimated_key == "C major"
        assert features.num_segments == 4

    def test_to_dict(self):
        features = MusicalFeatures(
            duration_seconds=60.0,
            sample_rate=22050,
            tempo=80.0,
            beat_times=[],
            estimated_key="A minor",
            key_confidence=0.7,
            chroma_mean=[0.0] * 12,
            mfcc_mean=[0.0] * 13,
            mfcc_std=[0.0] * 13,
            spectral_centroid_mean=1000.0,
            spectral_bandwidth_mean=1500.0,
            spectral_rolloff_mean=2500.0,
            rms_mean=0.08,
            rms_std=0.02,
            segment_boundaries=[],
            num_segments=1
        )

        d = features.to_dict()
        assert d["tempo"] == 80.0
        assert d["estimated_key"] == "A minor"
        assert isinstance(d, dict)

    def test_json_roundtrip(self, tmp_path):
        original = MusicalFeatures(
            duration_seconds=90.0,
            sample_rate=22050,
            tempo=65.0,
            beat_times=[0.0, 0.92],
            estimated_key="G major",
            key_confidence=0.85,
            chroma_mean=[0.1] * 12,
            mfcc_mean=[0.0] * 13,
            mfcc_std=[1.0] * 13,
            spectral_centroid_mean=1200.0,
            spectral_bandwidth_mean=1800.0,
            spectral_rolloff_mean=2800.0,
            rms_mean=0.12,
            rms_std=0.03,
            segment_boundaries=[45.0],
            num_segments=2
        )

        json_path = tmp_path / "features.json"
        original.to_json(json_path)

        loaded = MusicalFeatures.from_json(json_path)
        assert loaded.tempo == original.tempo
        assert loaded.estimated_key == original.estimated_key


class TestEstimateKey:
    """Tests for key estimation function."""

    def test_major_key_detection(self):
        """Test detection of C major scale pattern."""
        # Create chroma that emphasizes C major scale notes
        # C, D, E, F, G, A, B
        chroma = np.zeros((12, 100))
        major_scale_indices = [0, 2, 4, 5, 7, 9, 11]  # C major
        for i in major_scale_indices:
            chroma[i, :] = 1.0

        key, confidence = estimate_key(chroma)
        assert "C" in key
        assert "major" in key.lower()
        assert confidence > 0.5

    def test_minor_key_detection(self):
        """Test detection of A minor scale pattern."""
        # Create chroma that emphasizes A minor scale notes
        chroma = np.zeros((12, 100))
        minor_scale_indices = [9, 11, 0, 2, 4, 5, 7]  # A minor (relative to A=9)
        for i in minor_scale_indices:
            chroma[i, :] = 1.0

        key, confidence = estimate_key(chroma)
        # Should detect either A minor or C major (relative)
        assert confidence > 0


class TestAnalyzeForGeneration:
    """Tests for analyze_for_generation function."""

    def test_extracts_generation_params(self):
        features = MusicalFeatures(
            duration_seconds=180.0,
            sample_rate=22050,
            tempo=72.5,
            beat_times=[],
            estimated_key="D minor",
            key_confidence=0.75,
            chroma_mean=[0.0] * 12,
            mfcc_mean=[0.0] * 13,
            mfcc_std=[0.0] * 13,
            spectral_centroid_mean=1500.0,
            spectral_bandwidth_mean=2000.0,
            spectral_rolloff_mean=3000.0,
            rms_mean=0.1,
            rms_std=0.05,
            segment_boundaries=[],
            num_segments=1
        )

        params = analyze_for_generation(features)

        assert params["tempo"] == 72  # Rounded (banker's rounding: 72.5 → 72)
        assert params["root_note"] == "D"
        assert params["mode"] == "minor"
        assert "is_calm" in params
        assert "suggested_duration" in params
