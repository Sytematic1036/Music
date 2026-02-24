"""
Main pipeline module.

Orchestrates the complete flow:
1. Search YouTube for relaxation music
2. Download audio for analysis
3. Analyze musical features
4. Generate new MIDI music with variations
"""

import argparse
import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .youtube_search import search_relaxation_music, VideoResult
from .downloader import download_audio, cleanup_downloads, DownloadResult
from .analyzer import analyze_audio, analyze_for_generation, MusicalFeatures
from .generator import generate_from_analysis, generate_relaxation_midi, GenerationParams


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""
    success: bool
    search_results: list[VideoResult]
    downloaded_files: list[str]
    analyses: list[dict]
    generated_files: list[str]
    errors: list[str]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "search_results": [
                {"title": v.title, "url": v.url, "views": v.view_count}
                for v in self.search_results
            ],
            "downloaded_files": self.downloaded_files,
            "analyses": self.analyses,
            "generated_files": self.generated_files,
            "errors": self.errors,
            "timestamp": self.timestamp
        }

    def save(self, path: str | Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


def run_pipeline(
    search_query: str = "relaxation music",
    limit: int = 3,
    output_dir: str | Path = "output",
    download_audio_files: bool = True,
    generate_variations: int = 1,
    variation_amount: float = 0.3,
    duration_seconds: int = 120,
    cleanup_after: bool = True
) -> PipelineResult:
    """
    Run the complete relaxation music generation pipeline.

    Args:
        search_query: YouTube search query
        limit: Number of videos to analyze
        output_dir: Directory for output files
        download_audio_files: Whether to download and analyze audio
        generate_variations: Number of MIDI variations to generate per source
        variation_amount: How much to vary from source (0-1)
        duration_seconds: Duration of generated music
        cleanup_after: Whether to delete downloaded audio files after

    Returns:
        PipelineResult with all outputs and errors
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = []
    search_results = []
    downloaded_files = []
    analyses = []
    generated_files = []

    # Step 1: Search YouTube
    logger.info(f"Searching YouTube for: {search_query}")
    try:
        search_results = search_relaxation_music(
            query=search_query,
            limit=limit,
            min_duration_minutes=3,
            max_duration_minutes=15
        )
        logger.info(f"Found {len(search_results)} videos")
    except Exception as e:
        errors.append(f"Search failed: {str(e)}")
        logger.error(f"Search failed: {e}")

    if not search_results:
        # Generate with default parameters if no search results
        logger.warning("No search results, using default parameters")
        params = GenerationParams(
            tempo=70,
            root_note="C",
            mode="major",
            duration_seconds=duration_seconds,
            variation_amount=variation_amount
        )
        output_path = output_dir / "generated_default.mid"
        try:
            generate_relaxation_midi(params, output_path)
            generated_files.append(str(output_path))
            logger.info(f"Generated default: {output_path}")
        except Exception as e:
            errors.append(f"Generation failed: {str(e)}")

        return PipelineResult(
            success=len(generated_files) > 0,
            search_results=search_results,
            downloaded_files=downloaded_files,
            analyses=analyses,
            generated_files=generated_files,
            errors=errors,
            timestamp=datetime.now().isoformat()
        )

    # Step 2: Download and analyze audio
    if download_audio_files:
        download_dir = tempfile.mkdtemp(prefix="music_download_")

        for i, video in enumerate(search_results):
            logger.info(f"Processing {i + 1}/{len(search_results)}: {video.title}")

            # Download
            try:
                result = download_audio(
                    url=video.url,
                    output_dir=download_dir,
                    max_duration_seconds=600
                )

                if result.success and result.file_path:
                    downloaded_files.append(result.file_path)
                    logger.info(f"Downloaded: {result.file_path}")

                    # Analyze
                    try:
                        features = analyze_audio(result.file_path)
                        gen_params = analyze_for_generation(features)
                        gen_params["source_video"] = video.title
                        analyses.append(gen_params)
                        logger.info(f"Analyzed: tempo={gen_params['tempo']}, key={gen_params['root_note']} {gen_params['mode']}")

                        # Generate variations
                        for j in range(generate_variations):
                            output_name = f"generated_{i + 1}_v{j + 1}.mid"
                            output_path = output_dir / output_name
                            try:
                                generate_from_analysis(
                                    gen_params,
                                    output_path,
                                    variation=variation_amount,
                                    duration_override=duration_seconds
                                )
                                generated_files.append(str(output_path))
                                logger.info(f"Generated: {output_path}")
                            except Exception as e:
                                errors.append(f"Generation failed for {video.title}: {str(e)}")
                                logger.error(f"Generation error: {e}")

                    except Exception as e:
                        errors.append(f"Analysis failed for {video.title}: {str(e)}")
                        logger.error(f"Analysis error: {e}")
                else:
                    errors.append(f"Download failed for {video.title}: {result.error}")
                    logger.error(f"Download failed: {result.error}")

            except Exception as e:
                errors.append(f"Processing failed for {video.title}: {str(e)}")
                logger.error(f"Processing error: {e}")

        # Cleanup downloads if requested
        if cleanup_after:
            cleanup_downloads(download_dir)
            logger.info("Cleaned up downloaded files")

    else:
        # Generate without analysis using metadata hints
        for i, video in enumerate(search_results):
            # Use default calm parameters
            params = GenerationParams(
                tempo=65,
                root_note="C",
                mode="major",
                duration_seconds=duration_seconds,
                variation_amount=variation_amount
            )

            for j in range(generate_variations):
                output_name = f"generated_{i + 1}_v{j + 1}.mid"
                output_path = output_dir / output_name
                try:
                    generate_relaxation_midi(params, output_path, seed=i * 100 + j)
                    generated_files.append(str(output_path))
                    logger.info(f"Generated: {output_path}")
                except Exception as e:
                    errors.append(f"Generation failed: {str(e)}")

    # Save analysis summary
    if analyses:
        summary_path = output_dir / "analysis_summary.json"
        with open(summary_path, "w") as f:
            json.dump(analyses, f, indent=2)
        logger.info(f"Saved analysis summary: {summary_path}")

    return PipelineResult(
        success=len(generated_files) > 0,
        search_results=search_results,
        downloaded_files=downloaded_files,
        analyses=analyses,
        generated_files=generated_files,
        errors=errors,
        timestamp=datetime.now().isoformat()
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate relaxation music based on YouTube analysis"
    )
    parser.add_argument(
        "--search", "-s",
        default="relaxation music",
        help="YouTube search query"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=3,
        help="Number of videos to analyze"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip audio download (use default parameters)"
    )
    parser.add_argument(
        "--variations", "-v",
        type=int,
        default=1,
        help="Number of variations to generate per source"
    )
    parser.add_argument(
        "--variation-amount",
        type=float,
        default=0.3,
        help="How much to vary from source (0-1)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=120,
        help="Duration of generated music in seconds"
    )
    parser.add_argument(
        "--keep-downloads",
        action="store_true",
        help="Keep downloaded audio files"
    )

    args = parser.parse_args()

    result = run_pipeline(
        search_query=args.search,
        limit=args.limit,
        output_dir=args.output,
        download_audio_files=not args.no_download,
        generate_variations=args.variations,
        variation_amount=args.variation_amount,
        duration_seconds=args.duration,
        cleanup_after=not args.keep_downloads
    )

    # Print summary
    print("\n" + "=" * 50)
    print("Pipeline Complete")
    print("=" * 50)
    print(f"Success: {result.success}")
    print(f"Videos found: {len(result.search_results)}")
    print(f"Files downloaded: {len(result.downloaded_files)}")
    print(f"Files analyzed: {len(result.analyses)}")
    print(f"MIDI files generated: {len(result.generated_files)}")

    if result.generated_files:
        print("\nGenerated files:")
        for f in result.generated_files:
            print(f"  - {f}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  - {e}")

    # Save result
    result.save(Path(args.output) / "pipeline_result.json")

    return 0 if result.success else 1


if __name__ == "__main__":
    exit(main())
