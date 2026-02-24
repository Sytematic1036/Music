"""
Audio analysis module using librosa.

Extracts musical features from audio files:
- Tempo and beat positions
- Key/mode estimation
- Spectral features (MFCC, chroma)
- Structural segments
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class MusicalFeatures:
    """Extracted musical features from audio."""
    # Basic info
    duration_seconds: float
    sample_rate: int

    # Rhythm
    tempo: float
    beat_times: list[float]

    # Harmony
    estimated_key: str
    key_confidence: float
    chroma_mean: list[float]  # 12 values for each pitch class

    # Timbre
    mfcc_mean: list[float]
    mfcc_std: list[float]

    # Spectral
    spectral_centroid_mean: float
    spectral_bandwidth_mean: float
    spectral_rolloff_mean: float

    # Energy
    rms_mean: float
    rms_std: float

    # Structure
    segment_boundaries: list[float]
    num_segments: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        """Save to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: str | Path) -> "MusicalFeatures":
        """Load from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


# Key names for display
KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODE_NAMES = ["minor", "major"]


def estimate_key(chroma: np.ndarray) -> tuple[str, float]:
    """
    Estimate the musical key from chroma features.

    Uses the Krumhansl-Schmuckler key-finding algorithm.

    Args:
        chroma: Chroma feature array (12 x time)

    Returns:
        Tuple of (key name like "C major", confidence 0-1)
    """
    # Krumhansl-Schmuckler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    # Average chroma over time
    chroma_mean = np.mean(chroma, axis=1)

    best_corr = -1
    best_key = 0
    best_mode = 0

    # Test all 24 keys (12 major + 12 minor)
    for key in range(12):
        # Rotate profiles to match key
        major_rotated = np.roll(major_profile, key)
        minor_rotated = np.roll(minor_profile, key)

        # Correlation with major
        corr_major = np.corrcoef(chroma_mean, major_rotated)[0, 1]
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = key
            best_mode = 1  # major

        # Correlation with minor
        corr_minor = np.corrcoef(chroma_mean, minor_rotated)[0, 1]
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = key
            best_mode = 0  # minor

    key_name = f"{KEY_NAMES[best_key]} {MODE_NAMES[best_mode]}"
    confidence = max(0, min(1, (best_corr + 1) / 2))  # Normalize to 0-1

    return key_name, confidence


def analyze_audio(
    file_path: str | Path,
    sr: int = 22050,
    hop_length: int = 512,
    n_mfcc: int = 13
) -> MusicalFeatures:
    """
    Analyze an audio file and extract musical features.

    Args:
        file_path: Path to audio file (WAV, MP3, etc.)
        sr: Sample rate to use
        hop_length: Hop length for feature extraction
        n_mfcc: Number of MFCC coefficients

    Returns:
        MusicalFeatures object with extracted features
    """
    try:
        import librosa
    except ImportError:
        raise ImportError(
            "librosa is required. Install with: pip install librosa"
        )

    # Load audio
    y, sr = librosa.load(str(file_path), sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)

    # Tempo and beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length).tolist()

    # Handle numpy scalar for tempo
    if hasattr(tempo, 'item'):
        tempo = tempo.item()

    # Chroma features (for key detection)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    chroma_mean = np.mean(chroma, axis=1).tolist()

    # Key estimation
    estimated_key, key_confidence = estimate_key(chroma)

    # MFCC features (timbre)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, hop_length=hop_length)
    mfcc_mean = np.mean(mfcc, axis=1).tolist()
    mfcc_std = np.std(mfcc, axis=1).tolist()

    # Spectral features
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)

    # RMS energy
    rms = librosa.feature.rms(y=y, hop_length=hop_length)

    # Structural segmentation
    # Use spectral clustering on self-similarity matrix
    try:
        # Compute mel spectrogram for segmentation
        S = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=hop_length)
        S_db = librosa.power_to_db(S, ref=np.max)

        # Compute recurrence matrix
        R = librosa.segment.recurrence_matrix(S_db, mode='affinity', sym=True)

        # Find segment boundaries using novelty-based segmentation
        novelty = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        # Simple peak picking for segment boundaries
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(novelty, distance=sr // hop_length * 5)  # Min 5 seconds apart
        segment_boundaries = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length).tolist()
    except Exception:
        segment_boundaries = []

    return MusicalFeatures(
        duration_seconds=duration,
        sample_rate=sr,
        tempo=float(tempo),
        beat_times=beat_times,
        estimated_key=estimated_key,
        key_confidence=float(key_confidence),
        chroma_mean=chroma_mean,
        mfcc_mean=mfcc_mean,
        mfcc_std=mfcc_std,
        spectral_centroid_mean=float(np.mean(spectral_centroid)),
        spectral_bandwidth_mean=float(np.mean(spectral_bandwidth)),
        spectral_rolloff_mean=float(np.mean(spectral_rolloff)),
        rms_mean=float(np.mean(rms)),
        rms_std=float(np.std(rms)),
        segment_boundaries=segment_boundaries,
        num_segments=len(segment_boundaries) + 1
    )


def analyze_for_generation(features: MusicalFeatures) -> dict:
    """
    Extract key parameters for music generation from analyzed features.

    Returns a simplified dict with generation parameters.
    """
    # Determine mood based on key and spectral features
    is_minor = "minor" in features.estimated_key.lower()
    is_calm = features.spectral_centroid_mean < 2000  # Low brightness = calm

    # Extract root note from key
    key_parts = features.estimated_key.split()
    root_note = key_parts[0] if key_parts else "C"
    mode = key_parts[1] if len(key_parts) > 1 else "major"

    return {
        "tempo": round(features.tempo),
        "root_note": root_note,
        "mode": mode,
        "is_calm": is_calm,
        "energy_level": features.rms_mean,
        "brightness": features.spectral_centroid_mean,
        "suggested_duration": min(180, features.duration_seconds),  # Max 3 min for generated
        "beat_count": len(features.beat_times),
        "segment_count": features.num_segments
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(f"Analyzing: {sys.argv[1]}")
        features = analyze_audio(sys.argv[1])
        print(f"Tempo: {features.tempo:.1f} BPM")
        print(f"Key: {features.estimated_key} (confidence: {features.key_confidence:.2f})")
        print(f"Duration: {features.duration_seconds:.1f}s")
        print(f"Segments: {features.num_segments}")
    else:
        print("Usage: python analyzer.py <audio_file>")
