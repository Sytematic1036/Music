"""
Integrated music pipeline: Melody → Arrangement → Production.

Connects all modules and provides:
- Step-by-step generation with preview at each stage
- Full pipeline execution
- Learning integration
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .melody import (
    Melody,
    MelodyParams,
    generate_melody,
    generate_melody_for_genre,
    melody_to_midi,
    GENRE_PRESETS as MELODY_PRESETS
)
from .arrangement import (
    Arrangement,
    ArrangementParams,
    arrange_melody,
    arrangement_to_midi,
    get_arrangement_summary
)
from .production import (
    ProductionParams,
    ProductionPreset,
    ProductionResult,
    produce_arrangement,
    produce_midi_file,
    GENRE_MIX_PRESETS,
    get_production_info
)
from .player import (
    PlaybackMethod,
    PlaybackResult,
    play,
    play_with_browser,
    create_browser_player,
    get_player_info
)
from .learning import (
    LearningDatabase,
    GenerationRecord,
    create_record_from_generation
)


@dataclass
class PipelineStage:
    """Represents a stage in the pipeline."""
    name: str
    status: str = "pending"  # pending, in_progress, completed, error
    midi_path: Optional[str] = None
    audio_path: Optional[str] = None
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Complete pipeline result."""
    success: bool
    stages: dict[str, PipelineStage]
    final_midi_path: Optional[str] = None
    final_audio_path: Optional[str] = None
    generation_id: Optional[str] = None
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stages": {
                name: {
                    "status": stage.status,
                    "midi_path": stage.midi_path,
                    "audio_path": stage.audio_path,
                    "data": stage.data,
                    "error": stage.error
                }
                for name, stage in self.stages.items()
            },
            "final_midi_path": self.final_midi_path,
            "final_audio_path": self.final_audio_path,
            "generation_id": self.generation_id,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors
        }


class MusicPipeline:
    """
    Complete music generation pipeline.

    Stages:
    1. Melody - Generate melodic content
    2. Arrangement - Add instruments and harmony
    3. Production - Mix, master, and export audio
    """

    def __init__(
        self,
        output_dir: str | Path,
        enable_learning: bool = True,
        db_path: Optional[str] = None
    ):
        """
        Initialize pipeline.

        Args:
            output_dir: Directory for all output files
            enable_learning: Whether to save generations to learning DB
            db_path: Path to learning database
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.enable_learning = enable_learning
        self.db = LearningDatabase(db_path) if enable_learning else None

        # Stage outputs
        self.melody: Optional[Melody] = None
        self.arrangement: Optional[Arrangement] = None
        self.production_result: Optional[ProductionResult] = None

        # Parameters
        self.melody_params: Optional[MelodyParams] = None
        self.arrangement_params: Optional[ArrangementParams] = None
        self.production_params: Optional[ProductionParams] = None

    def stage_melody(
        self,
        genre: str = "relaxation",
        duration_seconds: int = 60,
        root_note: str = "C",
        params: Optional[MelodyParams] = None,
        seed: Optional[int] = None,
        preview: bool = False,
        preview_method: PlaybackMethod = PlaybackMethod.BROWSER
    ) -> PipelineStage:
        """
        Stage 1: Generate melody.

        Args:
            genre: Genre preset to use
            duration_seconds: Length in seconds
            root_note: Key/root note
            params: Custom melody parameters (overrides genre preset)
            seed: Random seed for reproducibility
            preview: Whether to play preview
            preview_method: How to play preview

        Returns:
            PipelineStage with results
        """
        stage = PipelineStage(name="melody", status="in_progress")

        try:
            # Generate melody
            if params:
                self.melody_params = params
                self.melody = generate_melody(params, seed)
            else:
                self.melody = generate_melody_for_genre(genre, duration_seconds, root_note, seed)
                self.melody_params = self.melody.params

            # Export to MIDI
            midi_path = self.output_dir / "01_melody.mid"
            melody_to_midi(self.melody, midi_path)

            stage.midi_path = str(midi_path)
            stage.status = "completed"
            stage.data = {
                "notes": len(self.melody.notes),
                "motifs": len(self.melody.motifs),
                "uniqueness": self.melody.uniqueness_score,
                "tempo": self.melody.params.tempo,
                "mode": self.melody.params.mode,
                "root_note": self.melody.params.root_note
            }

            # Preview if requested
            if preview:
                play(midi_path, preview_method)

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)

        return stage

    def stage_arrangement(
        self,
        genre: Optional[str] = None,
        params: Optional[ArrangementParams] = None,
        seed: Optional[int] = None,
        preview: bool = False,
        preview_method: PlaybackMethod = PlaybackMethod.BROWSER
    ) -> PipelineStage:
        """
        Stage 2: Create arrangement from melody.

        Args:
            genre: Genre for instrument selection
            params: Custom arrangement parameters
            seed: Random seed
            preview: Whether to play preview
            preview_method: How to play preview

        Returns:
            PipelineStage with results
        """
        stage = PipelineStage(name="arrangement", status="in_progress")

        if not self.melody:
            stage.status = "error"
            stage.error = "No melody generated. Run stage_melody first."
            return stage

        try:
            # Determine parameters
            if params:
                self.arrangement_params = params
            else:
                self.arrangement_params = ArrangementParams(
                    genre=genre or "relaxation",
                    tempo=self.melody.params.tempo,
                    root_note=self.melody.params.root_note,
                    mode=self.melody.params.mode,
                    duration_seconds=self.melody.params.duration_seconds
                )

            # Create arrangement
            self.arrangement = arrange_melody(self.melody, self.arrangement_params, seed)

            # Export to MIDI
            midi_path = self.output_dir / "02_arrangement.mid"
            arrangement_to_midi(self.arrangement, midi_path)

            stage.midi_path = str(midi_path)
            stage.status = "completed"
            stage.data = get_arrangement_summary(self.arrangement)

            # Preview if requested
            if preview:
                play(midi_path, preview_method)

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)

        return stage

    def stage_production(
        self,
        preset: Optional[ProductionPreset] = None,
        params: Optional[ProductionParams] = None,
        export_wav: bool = True,
        export_mp3: bool = True,
        preview: bool = False,
        preview_method: PlaybackMethod = PlaybackMethod.BROWSER
    ) -> PipelineStage:
        """
        Stage 3: Produce audio from arrangement.

        Args:
            preset: Production preset
            params: Custom production parameters
            export_wav: Export WAV file
            export_mp3: Export MP3 file
            preview: Whether to play preview
            preview_method: How to play preview

        Returns:
            PipelineStage with results
        """
        stage = PipelineStage(name="production", status="in_progress")

        if not self.arrangement:
            stage.status = "error"
            stage.error = "No arrangement created. Run stage_arrangement first."
            return stage

        try:
            # Determine parameters
            if params:
                self.production_params = params
            else:
                genre = self.arrangement_params.genre if self.arrangement_params else "relaxation"
                preset = preset or ProductionPreset(genre) if genre in [p.value for p in ProductionPreset] else ProductionPreset.RELAXATION
                self.production_params = ProductionParams(
                    preset=preset,
                    export_wav=export_wav,
                    export_mp3=export_mp3
                )
                self.production_params.mix_settings = GENRE_MIX_PRESETS.get(preset)

            # Produce audio
            production_dir = self.output_dir / "03_production"
            self.production_result = produce_arrangement(
                self.arrangement,
                production_dir,
                self.production_params
            )

            stage.status = "completed" if self.production_result.success else "error"
            stage.audio_path = self.production_result.wav_path or self.production_result.mp3_path
            stage.data = {
                "wav_path": self.production_result.wav_path,
                "mp3_path": self.production_result.mp3_path,
                "duration": self.production_result.duration_seconds,
                "errors": self.production_result.errors
            }

            if not self.production_result.success:
                stage.error = "; ".join(self.production_result.errors)

            # Preview if requested and successful
            if preview and stage.audio_path:
                play(stage.audio_path, preview_method)

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)

        return stage

    def run_full_pipeline(
        self,
        genre: str = "relaxation",
        duration_seconds: int = 60,
        root_note: str = "C",
        seed: Optional[int] = None,
        preview_stages: bool = False,
        save_to_learning: bool = True
    ) -> PipelineResult:
        """
        Run complete pipeline: melody → arrangement → production.

        Args:
            genre: Genre for all stages
            duration_seconds: Total duration
            root_note: Key/root note
            seed: Random seed
            preview_stages: Preview at each stage
            save_to_learning: Save to learning database

        Returns:
            PipelineResult with all outputs
        """
        result = PipelineResult(
            success=False,
            stages={}
        )

        # Stage 1: Melody
        print("Stage 1: Generating melody...")
        melody_stage = self.stage_melody(
            genre=genre,
            duration_seconds=duration_seconds,
            root_note=root_note,
            seed=seed,
            preview=preview_stages
        )
        result.stages["melody"] = melody_stage

        if melody_stage.status != "completed":
            result.errors.append(f"Melody failed: {melody_stage.error}")
            return result

        # Stage 2: Arrangement
        print("Stage 2: Creating arrangement...")
        arrangement_stage = self.stage_arrangement(
            genre=genre,
            seed=seed,
            preview=preview_stages
        )
        result.stages["arrangement"] = arrangement_stage

        if arrangement_stage.status != "completed":
            result.errors.append(f"Arrangement failed: {arrangement_stage.error}")
            return result

        # Stage 3: Production
        print("Stage 3: Producing audio...")
        production_stage = self.stage_production(
            preview=preview_stages
        )
        result.stages["production"] = production_stage

        if production_stage.status != "completed":
            result.errors.append(f"Production failed: {production_stage.error}")
            # Still consider partial success if MIDI exists
            result.final_midi_path = arrangement_stage.midi_path
        else:
            result.final_midi_path = arrangement_stage.midi_path
            result.final_audio_path = production_stage.audio_path
            result.success = True

        result.duration_seconds = duration_seconds

        # Save to learning database
        if save_to_learning and self.db and self.melody and self.arrangement and self.production_params:
            record = create_record_from_generation(
                self.melody,
                self.arrangement,
                self.production_params,
                result.final_midi_path,
                result.final_audio_path
            )
            self.db.save_generation(record)
            result.generation_id = record.id
            print(f"Saved to learning DB: {record.id}")

        return result

    def preview_stage(
        self,
        stage_name: str,
        method: PlaybackMethod = PlaybackMethod.BROWSER
    ) -> PlaybackResult:
        """
        Preview a specific stage.

        Args:
            stage_name: "melody", "arrangement", or "production"
            method: Playback method

        Returns:
            PlaybackResult
        """
        paths = {
            "melody": self.output_dir / "01_melody.mid",
            "arrangement": self.output_dir / "02_arrangement.mid",
            "production": self.output_dir / "03_production" / "production.wav"
        }

        path = paths.get(stage_name)
        if not path or not path.exists():
            return PlaybackResult(
                success=False,
                method=method,
                message=f"Stage '{stage_name}' not available"
            )

        return play(path, method)

    def create_player_page(self) -> str:
        """
        Create a browser player page with all stages.

        Returns:
            Path to player HTML
        """
        return create_browser_player(self.output_dir)

    def rate_generation(self, rating: int, comment: str = "") -> bool:
        """
        Rate the current generation.

        Args:
            rating: 1-5 stars
            comment: Optional feedback

        Returns:
            True if saved
        """
        if not self.db:
            return False

        # Find most recent generation
        stats = self.db.get_stats()
        if stats["total_generations"] == 0:
            return False

        # Get last generation ID (simple approach)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM generations ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return self.db.update_rating(row[0], rating, comment)

        return False

    def get_recommendations(self, genre: str) -> Optional[dict]:
        """
        Get recommended parameters based on learning.

        Args:
            genre: Target genre

        Returns:
            Recommended parameters or None
        """
        if not self.db:
            return None

        return self.db.get_best_params_for_genre(genre, min_rating=4)

    def close(self):
        """Clean up resources."""
        if self.db:
            self.db.close()


def create_quick_track(
    genre: str = "relaxation",
    duration: int = 60,
    output_dir: str = "output",
    preview: bool = True
) -> PipelineResult:
    """
    Quick function to create a complete track.

    Args:
        genre: Music genre
        duration: Duration in seconds
        output_dir: Output directory
        preview: Open browser player

    Returns:
        PipelineResult
    """
    pipeline = MusicPipeline(output_dir)

    result = pipeline.run_full_pipeline(
        genre=genre,
        duration_seconds=duration,
        preview_stages=False
    )

    if preview and result.success:
        pipeline.preview_stage("production", PlaybackMethod.BROWSER)

    pipeline.close()
    return result


if __name__ == "__main__":
    import sys

    genre = sys.argv[1] if len(sys.argv) > 1 else "relaxation"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    output = sys.argv[3] if len(sys.argv) > 3 else "output"

    print(f"Creating {genre} track ({duration}s)...")
    print("=" * 50)

    result = create_quick_track(genre, duration, output, preview=True)

    print("\n" + "=" * 50)
    print("Pipeline Complete")
    print("=" * 50)
    print(f"Success: {result.success}")

    for stage_name, stage in result.stages.items():
        status_icon = "✓" if stage.status == "completed" else "✗"
        print(f"  {status_icon} {stage_name}: {stage.status}")
        if stage.midi_path:
            print(f"      MIDI: {stage.midi_path}")
        if stage.audio_path:
            print(f"      Audio: {stage.audio_path}")

    if result.final_audio_path:
        print(f"\nFinal output: {result.final_audio_path}")

    if result.generation_id:
        print(f"Learning ID: {result.generation_id}")
