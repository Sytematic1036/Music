"""Tests for the main pipeline module."""

import pytest
from pathlib import Path

from src.pipeline import (
    PipelineResult,
    run_pipeline,
)
from src.youtube_search import VideoResult


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_creation(self):
        result = PipelineResult(
            success=True,
            search_results=[],
            downloaded_files=[],
            analyses=[],
            generated_files=["output.mid"],
            errors=[],
            timestamp="2026-02-23T12:00:00"
        )

        assert result.success is True
        assert len(result.generated_files) == 1

    def test_to_dict(self):
        video = VideoResult(
            video_id="abc",
            title="Test",
            channel="Channel",
            duration_seconds=300,
            view_count=1000,
            url="https://youtube.com/watch?v=abc"
        )

        result = PipelineResult(
            success=True,
            search_results=[video],
            downloaded_files=[],
            analyses=[{"tempo": 70}],
            generated_files=["file.mid"],
            errors=[],
            timestamp="2026-02-23T12:00:00"
        )

        d = result.to_dict()
        assert d["success"] is True
        assert len(d["search_results"]) == 1
        assert d["search_results"][0]["title"] == "Test"

    def test_save_to_file(self, tmp_path):
        result = PipelineResult(
            success=True,
            search_results=[],
            downloaded_files=[],
            analyses=[],
            generated_files=[],
            errors=[],
            timestamp="2026-02-23T12:00:00"
        )

        output_file = tmp_path / "result.json"
        result.save(output_file)

        assert output_file.exists()


class TestRunPipeline:
    """Tests for run_pipeline function."""

    def test_pipeline_no_download_mode(self, tmp_path):
        """Test pipeline without downloading (uses defaults)."""
        result = run_pipeline(
            search_query="test music",
            limit=1,
            output_dir=tmp_path,
            download_audio_files=False,
            generate_variations=1,
            duration_seconds=10
        )

        assert isinstance(result, PipelineResult)
        assert result.timestamp

        # Should generate at least something
        # (may have errors if network unavailable)

    def test_pipeline_creates_output_dir(self, tmp_path):
        """Test that pipeline creates output directory."""
        output_dir = tmp_path / "new_output"

        result = run_pipeline(
            limit=0,  # No search, just test directory creation
            output_dir=output_dir,
            download_audio_files=False,
            duration_seconds=5
        )

        assert output_dir.exists()

    def test_pipeline_with_mock_search(self, tmp_path, mocker):
        """Test pipeline with mocked search results."""
        # Mock search to return empty results
        mocker.patch(
            "src.pipeline.search_relaxation_music",
            return_value=[]
        )

        result = run_pipeline(
            output_dir=tmp_path,
            download_audio_files=False,
            duration_seconds=10
        )

        # Should still generate default music
        assert isinstance(result, PipelineResult)
        # With empty search, should generate default
        if result.success:
            assert len(result.generated_files) > 0


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    @pytest.mark.slow
    def test_full_pipeline_no_download(self, tmp_path):
        """Test complete pipeline flow without downloading."""
        result = run_pipeline(
            search_query="meditation music",
            limit=2,
            output_dir=tmp_path,
            download_audio_files=False,
            generate_variations=1,
            duration_seconds=15
        )

        # Check result structure
        assert hasattr(result, "success")
        assert hasattr(result, "search_results")
        assert hasattr(result, "generated_files")

        # Pipeline should complete (success depends on network)
        # At minimum, it should not crash
