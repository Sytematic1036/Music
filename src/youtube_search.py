"""
YouTube search module for finding relaxation music.

Uses youtube-search-python to search without API key.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoResult:
    """Represents a YouTube video search result."""
    video_id: str
    title: str
    channel: str
    duration_seconds: int
    view_count: int
    url: str
    thumbnail_url: Optional[str] = None


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds.
    Formats: "3:45", "1:23:45", "45"
    """
    if not duration_str:
        return 0

    parts = duration_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(parts[0])
    except (ValueError, IndexError):
        return 0


def parse_view_count(view_str: str) -> int:
    """
    Parse view count string to integer.
    Handles formats like "1,234,567 views", "1.2M views", "500K views"
    """
    if not view_str:
        return 0

    # Remove " views" suffix and commas
    clean = view_str.lower().replace(" views", "").replace(",", "").strip()

    try:
        # Handle K, M, B suffixes
        if clean.endswith("k"):
            return int(float(clean[:-1]) * 1_000)
        elif clean.endswith("m"):
            return int(float(clean[:-1]) * 1_000_000)
        elif clean.endswith("b"):
            return int(float(clean[:-1]) * 1_000_000_000)
        else:
            return int(clean)
    except (ValueError, IndexError):
        return 0


def search_relaxation_music(
    query: str = "relaxation music",
    limit: int = 10,
    min_duration_minutes: int = 3,
    max_duration_minutes: int = 60
) -> list[VideoResult]:
    """
    Search YouTube for relaxation music videos.

    Args:
        query: Search query (default: "relaxation music")
        limit: Maximum number of results to return
        min_duration_minutes: Minimum video duration in minutes
        max_duration_minutes: Maximum video duration in minutes

    Returns:
        List of VideoResult objects sorted by view count (descending)
    """
    try:
        from youtubesearchpython import VideosSearch
    except ImportError:
        raise ImportError(
            "youtube-search-python is required. "
            "Install with: pip install youtube-search-python"
        )

    # Search with more results to filter by duration
    search = VideosSearch(query, limit=limit * 3)
    raw_results = search.result().get("result", [])

    results = []
    min_seconds = min_duration_minutes * 60
    max_seconds = max_duration_minutes * 60

    for item in raw_results:
        duration = parse_duration(item.get("duration", "0"))

        # Filter by duration
        if duration < min_seconds or duration > max_seconds:
            continue

        # Get view count from accessibility data or viewCount field
        view_count_str = item.get("viewCount", {}).get("text", "0")
        if not view_count_str or view_count_str == "0":
            view_count_str = item.get("viewCount", {}).get("short", "0")

        video = VideoResult(
            video_id=item.get("id", ""),
            title=item.get("title", ""),
            channel=item.get("channel", {}).get("name", ""),
            duration_seconds=duration,
            view_count=parse_view_count(view_count_str),
            url=item.get("link", f"https://www.youtube.com/watch?v={item.get('id', '')}"),
            thumbnail_url=item.get("thumbnails", [{}])[0].get("url") if item.get("thumbnails") else None
        )
        results.append(video)

        if len(results) >= limit:
            break

    # Sort by view count (most popular first)
    results.sort(key=lambda x: x.view_count, reverse=True)

    return results


def get_top_relaxation_videos(
    categories: list[str] | None = None,
    limit_per_category: int = 5
) -> list[VideoResult]:
    """
    Get top relaxation videos across multiple categories.

    Args:
        categories: List of search queries. Defaults to common relaxation music types.
        limit_per_category: Number of videos per category

    Returns:
        List of unique VideoResult objects sorted by view count
    """
    if categories is None:
        categories = [
            "relaxation music",
            "meditation music",
            "sleep music",
            "calm piano music",
            "ambient relaxing music",
            "nature sounds relaxation"
        ]

    all_results = []
    seen_ids = set()

    for category in categories:
        try:
            videos = search_relaxation_music(
                query=category,
                limit=limit_per_category
            )
            for video in videos:
                if video.video_id not in seen_ids:
                    seen_ids.add(video.video_id)
                    all_results.append(video)
        except Exception:
            # Skip failed searches, continue with others
            continue

    # Sort by view count
    all_results.sort(key=lambda x: x.view_count, reverse=True)

    return all_results


if __name__ == "__main__":
    # Quick test
    print("Searching for relaxation music...")
    results = search_relaxation_music(limit=5)
    for i, video in enumerate(results, 1):
        print(f"{i}. {video.title}")
        print(f"   Channel: {video.channel}")
        print(f"   Views: {video.view_count:,}")
        print(f"   Duration: {video.duration_seconds // 60}:{video.duration_seconds % 60:02d}")
        print(f"   URL: {video.url}")
        print()
