"""Tests for integrated music pipeline."""

import pytest
from pathlib import Path
import tempfile

from src.music_pipeline import (
    MusicPipeline,
    PipelineStage,
    PipelineResult,
    create_quick_track,
)
from src.melody import MelodyParams
from src.arrangement import ArrangementParams
from src.production import ProductionPreset
from src.player import PlaybackMethod


class TestPipelineStage:
    """Tests for PipelineStage dataclass."""

    def test_default_values(self):
        stage = PipelineStage(name="test")
        assert stage.name == "test"
        assert stage.status == "pending"
        assert stage.midi_path is None
        assert stage.audio_path is None
        assert stage.error is None

    def test_completed_stage(self):
        stage = PipelineStage(
            name="melody",
            status="completed",
            midi_path="/path/to/melody.mid",
            data={"notes": 50, "uniqueness": 0.8}
        )
        assert stage.status == "completed"
        assert stage.data["notes"] == 50


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_success_result(self):
        result = PipelineResult(
            success=True,
            stages={
                "melody": PipelineStage(name="melody", status="completed"),
                "arrangement": PipelineStage(name="arrangement", status="completed"),
                "production": PipelineStage(name="production", status="completed"),
            },
            final_midi_path="/path/to/arrangement.mid",
            final_audio_path="/path/to/production.wav"
        )
        assert result.success is True
        assert len(result.stages) == 3

    def test_to_dict(self):
        result = PipelineResult(
            success=True,
            stages={
                "melody": PipelineStage(name="melody", status="completed"),
            }
        )
        d = result.to_dict()

        assert "success" in d
        assert "stages" in d
        assert "melody" in d["stages"]


class TestMusicPipeline:
    """Tests for MusicPipeline class."""

    @pytest.fixture
    def pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MusicPipeline(tmpdir, enable_learning=False)

    def test_create_pipeline(self, pipeline):
        assert pipeline.output_dir.exists()
        assert pipeline.melody is None
        assert pipeline.arrangement is None

    def test_stage_melody(self, pipeline):
        stage = pipeline.stage_melody(
            genre="relaxation",
            duration_seconds=15,
            seed=42
        )

        assert stage.status == "completed"
        assert stage.midi_path is not None
        assert Path(stage.midi_path).exists()
        assert "notes" in stage.data
        assert pipeline.melody is not None

    def test_stage_melody_with_custom_params(self, pipeline):
        params = MelodyParams(
            root_note="G",
            mode="minor",
            tempo=85,
            duration_seconds=15
        )
        stage = pipeline.stage_melody(params=params, seed=42)

        assert stage.status == "completed"
        assert pipeline.melody.params.root_note == "G"
        assert pipeline.melody.params.mode == "minor"

    def test_stage_arrangement_requires_melody(self, pipeline):
        stage = pipeline.stage_arrangement()

        assert stage.status == "error"
        assert "melody" in stage.error.lower()

    def test_stage_arrangement_after_melody(self, pipeline):
        pipeline.stage_melody(duration_seconds=15, seed=42)
        stage = pipeline.stage_arrangement(genre="relaxation", seed=42)

        assert stage.status == "completed"
        assert stage.midi_path is not None
        assert Path(stage.midi_path).exists()
        assert "num_tracks" in stage.data
        assert pipeline.arrangement is not None

    def test_stage_production_requires_arrangement(self, pipeline):
        stage = pipeline.stage_production()

        assert stage.status == "error"
        assert "arrangement" in stage.error.lower()


class TestMusicPipelineWithLearning:
    """Tests for pipeline with learning enabled."""

    @pytest.fixture
    def pipeline_with_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            pipeline = MusicPipeline(tmpdir, enable_learning=True, db_path=str(db_path))
            yield pipeline
            pipeline.close()

    def test_learning_enabled(self, pipeline_with_learning):
        assert pipeline_with_learning.db is not None

    def test_get_recommendations_empty(self, pipeline_with_learning):
        result = pipeline_with_learning.get_recommendations("relaxation")
        # No data yet, should return None
        assert result is None


class TestFullPipeline:
    """Tests for complete pipeline execution."""

    def test_run_full_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MusicPipeline(tmpdir, enable_learning=False)

            result = pipeline.run_full_pipeline(
                genre="relaxation",
                duration_seconds=15,
                seed=42,
                preview_stages=False,
                save_to_learning=False
            )

            assert result.stages["melody"].status == "completed"
            assert result.stages["arrangement"].status == "completed"
            # Production may fail if FluidSynth not installed
            assert result.final_midi_path is not None
            assert Path(result.final_midi_path).exists()

    def test_run_full_pipeline_all_genres(self):
        genres = ["relaxation", "ambient", "meditation", "lofi", "classical"]

        with tempfile.TemporaryDirectory() as tmpdir:
            for genre in genres:
                output_dir = Path(tmpdir) / genre
                pipeline = MusicPipeline(output_dir, enable_learning=False)

                result = pipeline.run_full_pipeline(
                    genre=genre,
                    duration_seconds=10,
                    seed=42,
                    preview_stages=False,
                    save_to_learning=False
                )

                assert result.stages["melody"].status == "completed"
                assert result.stages["arrangement"].status == "completed"


class TestPreviewStage:
    """Tests for stage preview functionality."""

    def test_preview_stage_not_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MusicPipeline(tmpdir, enable_learning=False)

            result = pipeline.preview_stage("melody", PlaybackMethod.BROWSER)

            assert result.success is False
            assert "not available" in result.message

    def test_preview_stage_after_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MusicPipeline(tmpdir, enable_learning=False)
            pipeline.stage_melody(duration_seconds=10, seed=42)

            result = pipeline.preview_stage("melody", PlaybackMethod.EXPORT)

            # Export should work if FluidSynth is available
            # Otherwise it will fail gracefully
            assert result.method == PlaybackMethod.EXPORT


class TestCreatePlayerPage:
    """Tests for player page creation."""

    def test_create_player_page(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MusicPipeline(tmpdir, enable_learning=False)
            player_path = pipeline.create_player_page()

            assert Path(player_path).exists()
            assert Path(player_path).name == "player.html"


class TestQuickTrack:
    """Tests for quick track creation function."""

    def test_create_quick_track(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_quick_track(
                genre="relaxation",
                duration=15,
                output_dir=tmpdir,
                preview=False
            )

            assert result.stages["melody"].status == "completed"
            assert result.stages["arrangement"].status == "completed"
            assert result.final_midi_path is not None


class TestPipelineReproducibility:
    """Tests for reproducible generation."""

    def test_same_seed_same_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "run1"
            dir2 = Path(tmpdir) / "run2"

            pipeline1 = MusicPipeline(dir1, enable_learning=False)
            result1 = pipeline1.run_full_pipeline(
                genre="relaxation",
                duration_seconds=10,
                seed=12345,
                preview_stages=False,
                save_to_learning=False
            )

            pipeline2 = MusicPipeline(dir2, enable_learning=False)
            result2 = pipeline2.run_full_pipeline(
                genre="relaxation",
                duration_seconds=10,
                seed=12345,
                preview_stages=False,
                save_to_learning=False
            )

            # Same seed should produce same melody
            assert result1.stages["melody"].data["notes"] == result2.stages["melody"].data["notes"]
            assert result1.stages["melody"].data["uniqueness"] == result2.stages["melody"].data["uniqueness"]
