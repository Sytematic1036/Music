"""
Learning module for music parameter optimization.

Uses vector database to:
- Store generation parameters and outcomes
- Find similar successful parameters
- Learn patterns from user feedback
- Recommend optimal parameters for new generations
"""

import json
import sqlite3
import struct
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib

from .melody import MelodyParams, Melody, GENRE_PRESETS as MELODY_PRESETS
from .arrangement import ArrangementParams, Arrangement
from .production import ProductionParams, MixSettings


@dataclass
class GenerationRecord:
    """Record of a generation with parameters and outcome."""
    id: str
    timestamp: str

    # Stage parameters
    melody_params: dict
    arrangement_params: dict
    production_params: dict

    # Metrics
    uniqueness_score: float = 0.0
    track_count: int = 0
    duration_seconds: float = 0.0

    # User feedback
    rating: Optional[int] = None  # 1-5 stars
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    # File paths
    midi_path: Optional[str] = None
    audio_path: Optional[str] = None

    def to_vector(self) -> list[float]:
        """
        Convert parameters to embedding vector for similarity search.

        Vector dimensions:
        - tempo (normalized 40-200 → 0-1)
        - mode (major=1, minor=0, others=0.5)
        - uniqueness
        - track_count (normalized)
        - duration (normalized)
        - rating (if any, else 0.5)
        - genre embedding (one-hot or similar)
        """
        vector = []

        # Tempo (40-200 BPM normalized)
        tempo = self.melody_params.get("tempo", 70)
        vector.append((tempo - 40) / 160)

        # Mode
        mode = self.melody_params.get("mode", "major")
        mode_val = {"major": 1.0, "minor": 0.0}.get(mode, 0.5)
        vector.append(mode_val)

        # Uniqueness
        vector.append(self.uniqueness_score)

        # Track count (1-10 normalized)
        vector.append(min(self.track_count / 10, 1.0))

        # Duration (0-300s normalized)
        vector.append(min(self.duration_seconds / 300, 1.0))

        # Rating
        if self.rating:
            vector.append((self.rating - 1) / 4)
        else:
            vector.append(0.5)

        # Genre (simplified one-hot for 6 genres)
        genres = ["relaxation", "ambient", "meditation", "lofi", "classical", "cinematic"]
        genre = self.arrangement_params.get("genre", "relaxation")
        for g in genres:
            vector.append(1.0 if g == genre else 0.0)

        # Production preset influence (reverb, compression, etc)
        mix = self.production_params.get("mix_settings", {})
        vector.append(mix.get("reverb_amount", 0.3))
        vector.append((mix.get("compression_ratio", 4) - 1) / 9)  # 1-10 normalized
        vector.append(mix.get("stereo_width", 1.0) / 2)

        # Pad to fixed length (16 dimensions)
        while len(vector) < 16:
            vector.append(0.0)

        return vector[:16]  # Ensure exactly 16 dims


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class LearningDatabase:
    """
    SQLite + vector storage for learning from generations.

    Stores:
    - Generation parameters
    - User ratings and feedback
    - Computed metrics

    Enables:
    - Similar parameter search
    - Best parameter recommendations
    - Learning trends
    """

    def __init__(self, db_path: str | Path = None):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path.home() / ".music_learning" / "generations.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Main records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                melody_params TEXT,
                arrangement_params TEXT,
                production_params TEXT,
                uniqueness_score REAL,
                track_count INTEGER,
                duration_seconds REAL,
                rating INTEGER,
                tags TEXT,
                notes TEXT,
                midi_path TEXT,
                audio_path TEXT,
                vector BLOB
            )
        """)

        # Tags index for filtering
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tag_index (
                tag TEXT,
                generation_id TEXT,
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)

        # Feedback history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id TEXT,
                timestamp TEXT,
                rating INTEGER,
                comment TEXT,
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)

        self.conn.commit()

    def _vector_to_blob(self, vector: list[float]) -> bytes:
        """Convert vector to binary blob."""
        return struct.pack(f'{len(vector)}f', *vector)

    def _blob_to_vector(self, blob: bytes) -> list[float]:
        """Convert binary blob to vector."""
        count = len(blob) // 4  # 4 bytes per float
        return list(struct.unpack(f'{count}f', blob))

    def save_generation(self, record: GenerationRecord) -> str:
        """
        Save a generation record.

        Args:
            record: GenerationRecord to save

        Returns:
            Record ID
        """
        cursor = self.conn.cursor()

        vector = record.to_vector()
        vector_blob = self._vector_to_blob(vector)

        cursor.execute("""
            INSERT OR REPLACE INTO generations
            (id, timestamp, melody_params, arrangement_params, production_params,
             uniqueness_score, track_count, duration_seconds, rating, tags, notes,
             midi_path, audio_path, vector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.timestamp,
            json.dumps(record.melody_params),
            json.dumps(record.arrangement_params),
            json.dumps(record.production_params),
            record.uniqueness_score,
            record.track_count,
            record.duration_seconds,
            record.rating,
            json.dumps(record.tags),
            record.notes,
            record.midi_path,
            record.audio_path,
            vector_blob
        ))

        # Update tag index
        for tag in record.tags:
            cursor.execute("""
                INSERT INTO tag_index (tag, generation_id) VALUES (?, ?)
            """, (tag.lower(), record.id))

        self.conn.commit()
        return record.id

    def get_generation(self, record_id: str) -> Optional[GenerationRecord]:
        """Get a generation by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM generations WHERE id = ?", (record_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return GenerationRecord(
            id=row[0],
            timestamp=row[1],
            melody_params=json.loads(row[2]),
            arrangement_params=json.loads(row[3]),
            production_params=json.loads(row[4]),
            uniqueness_score=row[5],
            track_count=row[6],
            duration_seconds=row[7],
            rating=row[8],
            tags=json.loads(row[9]) if row[9] else [],
            notes=row[10] or "",
            midi_path=row[11],
            audio_path=row[12]
        )

    def update_rating(self, record_id: str, rating: int, comment: str = "") -> bool:
        """
        Update rating for a generation.

        Args:
            record_id: Generation ID
            rating: 1-5 star rating
            comment: Optional feedback comment

        Returns:
            True if successful
        """
        cursor = self.conn.cursor()

        # Update main record
        cursor.execute("""
            UPDATE generations SET rating = ? WHERE id = ?
        """, (rating, record_id))

        # Add to feedback history
        cursor.execute("""
            INSERT INTO feedback (generation_id, timestamp, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (record_id, datetime.now().isoformat(), rating, comment))

        # Recompute vector with new rating
        record = self.get_generation(record_id)
        if record:
            record.rating = rating
            vector = record.to_vector()
            cursor.execute("""
                UPDATE generations SET vector = ? WHERE id = ?
            """, (self._vector_to_blob(vector), record_id))

        self.conn.commit()
        return True

    def find_similar(
        self,
        params: GenerationRecord | dict,
        limit: int = 5,
        min_rating: Optional[int] = None
    ) -> list[tuple[GenerationRecord, float]]:
        """
        Find similar generations by parameter similarity.

        Args:
            params: Reference parameters (GenerationRecord or dict with params)
            limit: Maximum results
            min_rating: Only return generations with this rating or higher

        Returns:
            List of (record, similarity_score) tuples
        """
        # Build query vector
        if isinstance(params, GenerationRecord):
            query_vector = params.to_vector()
        else:
            # Build from dict
            temp_record = GenerationRecord(
                id="query",
                timestamp="",
                melody_params=params.get("melody_params", {}),
                arrangement_params=params.get("arrangement_params", {}),
                production_params=params.get("production_params", {}),
                uniqueness_score=params.get("uniqueness_score", 0.5),
                track_count=params.get("track_count", 5),
                duration_seconds=params.get("duration_seconds", 60),
                rating=params.get("rating")
            )
            query_vector = temp_record.to_vector()

        # Get all records
        cursor = self.conn.cursor()

        if min_rating:
            cursor.execute("""
                SELECT id, vector FROM generations WHERE rating >= ?
            """, (min_rating,))
        else:
            cursor.execute("SELECT id, vector FROM generations")

        results = []
        for row in cursor.fetchall():
            record_id = row[0]
            stored_vector = self._blob_to_vector(row[1])

            similarity = cosine_similarity(query_vector, stored_vector)
            results.append((record_id, similarity))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)

        # Fetch full records
        output = []
        for record_id, similarity in results[:limit]:
            record = self.get_generation(record_id)
            if record:
                output.append((record, similarity))

        return output

    def get_best_params_for_genre(
        self,
        genre: str,
        min_rating: int = 4
    ) -> Optional[dict]:
        """
        Get best parameters for a genre based on highly-rated generations.

        Args:
            genre: Target genre
            min_rating: Minimum rating to consider

        Returns:
            Averaged/optimized parameters or None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT melody_params, arrangement_params, production_params, rating
            FROM generations
            WHERE rating >= ?
        """, (min_rating,))

        matching = []
        for row in cursor.fetchall():
            arr_params = json.loads(row[1])
            if arr_params.get("genre") == genre:
                matching.append({
                    "melody": json.loads(row[0]),
                    "arrangement": arr_params,
                    "production": json.loads(row[2]),
                    "rating": row[3]
                })

        if not matching:
            return None

        # Weight by rating and average numeric params
        total_weight = sum(m["rating"] for m in matching)

        def weighted_avg(key_path: list[str]) -> float:
            total = 0
            for m in matching:
                val = m
                for k in key_path:
                    val = val.get(k, {})
                if isinstance(val, (int, float)):
                    total += val * m["rating"]
            return total / total_weight if total_weight > 0 else 0

        return {
            "melody_params": {
                "tempo": int(weighted_avg(["melody", "tempo"])),
                "mode": matching[0]["melody"].get("mode", "major"),  # Use most common
                "note_density": weighted_avg(["melody", "note_density"]),
                "syncopation": weighted_avg(["melody", "syncopation"]),
            },
            "arrangement_params": {
                "genre": genre,
                "num_tracks": int(weighted_avg(["arrangement", "num_tracks"])),
            },
            "production_params": {
                "mix_settings": {
                    "reverb_amount": weighted_avg(["production", "mix_settings", "reverb_amount"]),
                    "compression_ratio": weighted_avg(["production", "mix_settings", "compression_ratio"]),
                    "stereo_width": weighted_avg(["production", "mix_settings", "stereo_width"]),
                }
            }
        }

    def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM generations")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(rating) FROM generations WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM generations WHERE rating >= 4")
        highly_rated = cursor.fetchone()[0]

        cursor.execute("""
            SELECT json_extract(arrangement_params, '$.genre'), COUNT(*)
            FROM generations
            GROUP BY json_extract(arrangement_params, '$.genre')
        """)
        genre_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_generations": total,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "highly_rated_count": highly_rated,
            "genre_distribution": genre_counts
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


def create_record_from_generation(
    melody: Melody,
    arrangement: Arrangement,
    production_params: ProductionParams,
    midi_path: Optional[str] = None,
    audio_path: Optional[str] = None
) -> GenerationRecord:
    """
    Create a GenerationRecord from generation outputs.

    Args:
        melody: Generated melody
        arrangement: Generated arrangement
        production_params: Production parameters used
        midi_path: Path to MIDI file
        audio_path: Path to audio file

    Returns:
        GenerationRecord ready for saving
    """
    # Generate unique ID
    id_data = f"{datetime.now().isoformat()}{melody.params.root_note}{melody.params.mode}"
    record_id = hashlib.md5(id_data.encode()).hexdigest()[:12]

    return GenerationRecord(
        id=record_id,
        timestamp=datetime.now().isoformat(),
        melody_params=asdict(melody.params),
        arrangement_params=asdict(arrangement.params),
        production_params={
            "preset": production_params.preset.value,
            "sample_rate": production_params.sample_rate,
            "mix_settings": asdict(production_params.mix_settings) if production_params.mix_settings else {}
        },
        uniqueness_score=melody.uniqueness_score,
        track_count=len(arrangement.tracks),
        duration_seconds=melody.params.duration_seconds,
        midi_path=midi_path,
        audio_path=audio_path
    )


if __name__ == "__main__":
    # Demo usage
    print("Learning Database Demo")
    print("=" * 50)

    db = LearningDatabase()

    # Create sample records
    for i in range(3):
        record = GenerationRecord(
            id=f"demo_{i}",
            timestamp=datetime.now().isoformat(),
            melody_params={
                "tempo": 60 + i * 10,
                "mode": "major" if i % 2 == 0 else "minor",
                "root_note": "C"
            },
            arrangement_params={
                "genre": ["relaxation", "ambient", "lofi"][i],
                "num_tracks": 5 + i
            },
            production_params={
                "preset": "relaxation",
                "mix_settings": {
                    "reverb_amount": 0.3 + i * 0.1,
                    "compression_ratio": 4,
                    "stereo_width": 1.0
                }
            },
            uniqueness_score=0.7 + i * 0.1,
            track_count=5 + i,
            duration_seconds=60 + i * 30,
            rating=3 + i,
            tags=["demo", f"test{i}"]
        )
        db.save_generation(record)
        print(f"Saved: {record.id}")

    # Find similar
    print("\nFinding similar to relaxation genre...")
    similar = db.find_similar({
        "melody_params": {"tempo": 65, "mode": "major"},
        "arrangement_params": {"genre": "relaxation"},
        "production_params": {}
    })
    for record, score in similar:
        print(f"  {record.id}: {score:.2f} similarity, rating={record.rating}")

    # Stats
    print("\nStats:")
    stats = db.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    db.close()
