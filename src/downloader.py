"""
Audio downloader module using yt-dlp.

Downloads audio from YouTube videos for analysis.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


def check_yt_dlp_installed() -> bool:
    """Check if yt-dlp is installed and accessible."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def download_audio(
    url: str,
    output_dir: str | Path | None = None,
    output_format: str = "wav",
    max_duration_seconds: int = 600,
    sample_rate: int = 22050
) -> DownloadResult:
    """
    Download audio from a YouTube video.

    Args:
        url: YouTube video URL or video ID
        output_dir: Directory to save the file. Uses temp dir if None.
        output_format: Output format (wav, mp3, m4a)
        max_duration_seconds: Maximum duration to download (default: 10 minutes)
        sample_rate: Audio sample rate for WAV output

    Returns:
        DownloadResult with file path or error message
    """
    if not check_yt_dlp_installed():
        return DownloadResult(
            success=False,
            error="yt-dlp is not installed. Install with: pip install yt-dlp"
        )

    # Normalize URL
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    # Set output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="music_")
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(Path(output_dir) / "%(id)s.%(ext)s")

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", output_format,
        "--audio-quality", "0",  # Best quality
        "--output", output_template,
        "--no-playlist",
        "--no-warnings",
        "--quiet",
    ]

    # Add duration limit if specified
    if max_duration_seconds > 0:
        cmd.extend(["--match-filter", f"duration<={max_duration_seconds}"])

    # Add post-processing for sample rate if WAV
    if output_format == "wav":
        cmd.extend([
            "--postprocessor-args",
            f"ffmpeg:-ar {sample_rate}"
        ])

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown download error"
            return DownloadResult(success=False, error=error_msg)

        # Find the downloaded file
        output_path = Path(output_dir)
        files = list(output_path.glob(f"*.{output_format}"))

        if not files:
            return DownloadResult(
                success=False,
                error="Download completed but no output file found"
            )

        downloaded_file = files[0]

        # Get duration using ffprobe if available
        duration = get_audio_duration(str(downloaded_file))

        return DownloadResult(
            success=True,
            file_path=str(downloaded_file),
            duration_seconds=duration
        )

    except subprocess.TimeoutExpired:
        return DownloadResult(success=False, error="Download timed out")
    except Exception as e:
        return DownloadResult(success=False, error=str(e))


def get_audio_duration(file_path: str) -> Optional[float]:
    """Get audio duration using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def download_multiple(
    urls: list[str],
    output_dir: str | Path,
    output_format: str = "wav",
    max_duration_seconds: int = 600
) -> list[DownloadResult]:
    """
    Download multiple audio files.

    Args:
        urls: List of YouTube URLs or video IDs
        output_dir: Directory to save files
        output_format: Output audio format
        max_duration_seconds: Maximum duration per video

    Returns:
        List of DownloadResult objects
    """
    results = []
    for url in urls:
        result = download_audio(
            url=url,
            output_dir=output_dir,
            output_format=output_format,
            max_duration_seconds=max_duration_seconds
        )
        results.append(result)
    return results


def cleanup_downloads(directory: str | Path) -> int:
    """
    Remove downloaded audio files from a directory.

    Returns:
        Number of files removed
    """
    directory = Path(directory)
    if not directory.exists():
        return 0

    count = 0
    for ext in ["wav", "mp3", "m4a", "webm", "opus"]:
        for file in directory.glob(f"*.{ext}"):
            try:
                file.unlink()
                count += 1
            except OSError:
                pass
    return count


if __name__ == "__main__":
    # Quick test with a known short video
    print("Testing audio download...")
    print("Note: Requires yt-dlp to be installed")

    if check_yt_dlp_installed():
        print("yt-dlp is installed")
    else:
        print("yt-dlp is NOT installed")
        print("Install with: pip install yt-dlp")
