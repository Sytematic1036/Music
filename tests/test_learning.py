"""Tests for learning module."""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime

from src.learning import (
    LearningDatabase,
    GenerationRecord,
    cosine_similarity,
    create_record_from_generation,
)
from src.melody import MelodyParams, generate_melody
from src.arrangement import ArrangementParams, arrange_melody
from src.production import ProductionParams, ProductionPreset


class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(v, v)
        assert abs(similarity - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(v1, v2)
        assert abs(similarity) < 0.001

    def test_opposite_vectors(self):
        v1 = [1.0, 2.0, 3.0]
        v2 = [-1.0, -2.0, -3.0]
        similarity = cosine_similarity(v1, v2)
        assert abs(similarity + 1.0) < 0.001

    def test_zero_vector(self):
        v1 = [1.0, 2.0]
        v2 = [0.0, 0.0]
        similarity = cosine_similarity(v1, v2)
        assert similarity == 0.0


class TestGenerationRecord:
    """Tests for GenerationRecord dataclass."""

    def test_create_record(self):
        record = GenerationRecord(
            id="test123",
            timestamp=datetime.now().isoformat(),
            melody_params={"tempo": 70, "mode": "major"},
            arrangement_params={"genre": "relaxation"},
            production_params={"preset": "relaxation"},
            uniqueness_score=0.8,
            track_count=5,
            duration_seconds=60
        )
        assert record.id == "test123"
        assert record.uniqueness_score == 0.8

    def test_to_vector_dimensions(self):
        record = GenerationRecord(
            id="test",
            timestamp="",
            melody_params={"tempo": 70, "mode": "major"},
            arrangement_params={"genre": "relaxation"},
            production_params={"mix_settings": {"reverb_amount": 0.3}},
            uniqueness_score=0.8,
            track_count=5,
            duration_seconds=60
        )
        vector = record.to_vector()
        assert len(vector) == 16  # Fixed dimension

    def test_to_vector_normalized(self):
        record = GenerationRecord(
            id="test",
            timestamp="",
            melody_params={"tempo": 120, "mode": "major"},
            arrangement_params={"genre": "relaxation"},
            production_params={},
            uniqueness_score=0.5,
            track_count=5,
            duration_seconds=60
        )
        vector = record.to_vector()
        # All values should be normalized to roughly 0-1
        for val in vector:
            assert -0.1 <= val <= 1.1


class TestLearningDatabase:
    """Tests for LearningDatabase."""

    @pytest.fixture
    def db(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = LearningDatabase(db_path)
            yield db
            db.close()

    def test_create_database(self, db):
        assert db.db_path.exists()

    def test_save_generation(self, db):
        record = GenerationRecord(
            id="test1",
            timestamp=datetime.now().isoformat(),
            melody_params={"tempo": 70, "mode": "major"},
            arrangement_params={"genre": "relaxation"},
            production_params={},
            uniqueness_score=0.8,
            track_count=5,
            duration_seconds=60
        )
        record_id = db.save_generation(record)
        assert record_id == "test1"

    def test_get_generation(self, db):
        record = GenerationRecord(
            id="test2",
            timestamp=datetime.now().isoformat(),
            melody_params={"tempo": 80, "mode": "minor"},
            arrangement_params={"genre": "ambient"},
            production_params={},
            uniqueness_score=0.7,
            track_count=6,
            duration_seconds=90,
            tags=["test", "ambient"]
        )
        db.save_generation(record)

        retrieved = db.get_generation("test2")
        assert retrieved is not None
        assert retrieved.id == "test2"
        assert retrieved.uniqueness_score == 0.7
        assert "test" in retrieved.tags

    def test_get_nonexistent_generation(self, db):
        result = db.get_generation("nonexistent")
        assert result is None

    def test_update_rating(self, db):
        record = GenerationRecord(
            id="test3",
            timestamp=datetime.now().isoformat(),
            melody_params={"tempo": 70},
            arrangement_params={"genre": "relaxation"},
            production_params={},
            uniqueness_score=0.8,
            track_count=5,
            duration_seconds=60
        )
        db.save_generation(record)

        success = db.update_rating("test3", 5, "Great!")
        assert success is True

        retrieved = db.get_generation("test3")
        assert retrieved.rating == 5

    def test_find_similar(self, db):
        # Create several records
        for i in range(5):
            record = GenerationRecord(
                id=f"sim_{i}",
                timestamp=datetime.now().isoformat(),
                melody_params={"tempo": 70 + i * 10, "mode": "major"},
                arrangement_params={"genre": "relaxation"},
                production_params={},
                uniqueness_score=0.7 + i * 0.05,
                track_count=5,
                duration_seconds=60
            )
            db.save_generation(record)

        # Find similar to one record
        query = {
            "melody_params": {"tempo": 75, "mode": "major"},
            "arrangement_params": {"genre": "relaxation"},
            "production_params": {}
        }
        similar = db.find_similar(query, limit=3)

        assert len(similar) <= 3
        if similar:
            record, score = similar[0]
            assert isinstance(record, GenerationRecord)
            assert 0 <= score <= 1

    def test_find_similar_with_min_rating(self, db):
        # Create records with different ratings
        for i in range(5):
            record = GenerationRecord(
                id=f"rated_{i}",
                timestamp=datetime.now().isoformat(),
                melody_params={"tempo": 70},
                arrangement_params={"genre": "relaxation"},
                production_params={},
                uniqueness_score=0.8,
                track_count=5,
                duration_seconds=60,
                rating=i + 1  # Ratings 1-5
            )
            db.save_generation(record)

        # Find only highly rated
        similar = db.find_similar(
            {"melody_params": {}, "arrangement_params": {}, "production_params": {}},
            min_rating=4
        )

        for record, _ in similar:
            assert record.rating >= 4

    def test_get_best_params_for_genre(self, db):
        # Create highly-rated relaxation tracks
        for i in range(3):
            record = GenerationRecord(
                id=f"best_{i}",
                timestamp=datetime.now().isoformat(),
                melody_params={"tempo": 65 + i * 5, "mode": "major"},
                arrangement_params={"genre": "relaxation", "num_tracks": 5 + i},
                production_params={"mix_settings": {"reverb_amount": 0.4}},
                uniqueness_score=0.8,
                track_count=5 + i,
                duration_seconds=60,
                rating=5
            )
            db.save_generation(record)

        best_params = db.get_best_params_for_genre("relaxation", min_rating=4)

        if best_params:
            assert "melody_params" in best_params
            assert "arrangement_params" in best_params

    def test_get_best_params_no_matches(self, db):
        result = db.get_best_params_for_genre("nonexistent_genre")
        assert result is None

    def test_get_stats(self, db):
        # Add some records
        for i in range(3):
            record = GenerationRecord(
                id=f"stat_{i}",
                timestamp=datetime.now().isoformat(),
                melody_params={},
                arrangement_params={"genre": "relaxation" if i < 2 else "ambient"},
                production_params={},
                uniqueness_score=0.8,
                track_count=5,
                duration_seconds=60,
                rating=4 if i < 2 else 3
            )
            db.save_generation(record)

        stats = db.get_stats()

        assert stats["total_generations"] == 3
        assert stats["highly_rated_count"] == 2
        assert "genre_distribution" in stats


class TestCreateRecordFromGeneration:
    """Tests for creating records from generation outputs."""

    def test_create_record(self):
        # Generate actual outputs
        melody_params = MelodyParams(duration_seconds=15)
        melody = generate_melody(melody_params, seed=42)

        arr_params = ArrangementParams(genre="relaxation")
        arrangement = arrange_melody(melody, arr_params)

        prod_params = ProductionParams(preset=ProductionPreset.RELAXATION)

        record = create_record_from_generation(
            melody=melody,
            arrangement=arrangement,
            production_params=prod_params,
            midi_path="/test/path.mid"
        )

        assert record.id is not None
        assert len(record.id) == 12
        assert record.uniqueness_score == melody.uniqueness_score
        assert record.track_count == len(arrangement.tracks)
        assert record.midi_path == "/test/path.mid"

    def test_record_has_correct_params(self):
        melody_params = MelodyParams(
            root_note="G",
            mode="minor",
            tempo=80,
            duration_seconds=15
        )
        melody = generate_melody(melody_params, seed=42)

        arr_params = ArrangementParams(genre="lofi")
        arrangement = arrange_melody(melody, arr_params)

        prod_params = ProductionParams(preset=ProductionPreset.LOFI)

        record = create_record_from_generation(melody, arrangement, prod_params)

        assert record.melody_params["root_note"] == "G"
        assert record.melody_params["mode"] == "minor"
        assert record.arrangement_params["genre"] == "lofi"
        assert record.production_params["preset"] == "lofi"


class TestVectorBlobConversion:
    """Tests for vector blob conversion in database."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = LearningDatabase(db_path)
            yield db
            db.close()

    def test_vector_roundtrip(self, db):
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        blob = db._vector_to_blob(vector)
        recovered = db._blob_to_vector(blob)

        assert len(recovered) == len(vector)
        for orig, rec in zip(vector, recovered):
            assert abs(orig - rec) < 0.0001
