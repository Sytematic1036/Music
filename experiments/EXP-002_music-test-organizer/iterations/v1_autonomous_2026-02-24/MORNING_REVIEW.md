# Autonom körning 2026-02-24

## Repo
`Music` (https://github.com/Sytematic1036/Music)

## Status
[x] LYCKADES / [ ] DELVIS / [ ] MISSLYCKADES

## Branch
`experiment/002-music-test-organizer`

## Sammanfattning

- **Mål 1 uppfyllt:** Skapade ett mappsystem för musiktester med löpnummer (test_001_, test_002_, etc.)
- **Mål 2 uppfyllt:** Skapade kategoriseringssystem för musik i undermappar:
  - by_genre/ (ambient, piano, nature, electronic, other)
  - by_tempo/ (slow <80 BPM, medium 80-120 BPM, fast >120 BPM)
  - by_mood/ (calm, energetic, focus, melancholic)
  - by_source/ (generated, youtube, original)

## Nya filer

### src/organizer.py
Ny modul med:
- `MusicOrganizer` klass för att organisera musikfiler
- `TempoCategory`, `GenreCategory`, `MoodCategory`, `SourceCategory` enums
- `TestFileInfo` dataclass för testfiler med löpnummer
- Automatisk kategorisering baserat på tempo, genre, mood, source
- Hantering av duplicerade filnamn (suffix _1, _2, etc.)
- Metadata-sparning och laddning (JSON)
- Statistik över kategorier

### Testfiler (5 st med löpnummer)
- `tests/test_001_directory_structure.py` - 8 tester
- `tests/test_002_categorization_logic.py` - 31 tester
- `tests/test_003_file_operations.py` - 13 tester
- `tests/test_004_test_numbering.py` - 11 tester
- `tests/test_005_integration.py` - 15 tester
- `tests/conftest.py` - Pytest-konfiguration

### Experiment-dokumentation
- `experiments/EXP-002_music-test-organizer/EXPERIMENT.md`
- `experiments/EXP-002_music-test-organizer/fixtures/success_criteria.yaml`
- `experiments/EXP-002_music-test-organizer/learnings.md`

## Tester

```
pytest tests/ -v
======================== 109 passed, 3 skipped in 1.46s ========================
```

Alla 67 nya tester + 42 befintliga tester passerar.

## Ändringar i befintlig kod

Inga ändringar i befintlig kod - endast nya filer tillagda.

## Användningsexempel

```python
from src.organizer import MusicOrganizer, setup_test_structure

# Skapa och setup mappstruktur
organizer = MusicOrganizer(base_path="music_library")
organizer.setup_directories()

# Kategorisera en fil
destinations = organizer.organize_file(
    "song.wav",
    tempo=85.0,        # -> by_tempo/medium/
    genre="ambient",   # -> by_genre/ambient/
    mood="calm",       # -> by_mood/calm/
    source="generated" # -> by_source/generated/
)

# Skapa testfiler med löpnummer
test = organizer.create_test_file(
    name="new_feature",
    description="Test new feature",
    test_dir="tests"
)
# -> test_006_new_feature.py (nästa lediga nummer)

# Hämta statistik
stats = organizer.get_category_stats()
```

## Nästa steg för användaren

1. **Granska ändringar:**
   ```bash
   cd C:\Users\haege\Music\.worktrees\002-music-test-organizer
   git diff main...experiment/002-music-test-organizer
   ```

2. **Om OK, pusha och skapa PR:**
   ```bash
   git push -u origin experiment/002-music-test-organizer
   gh pr create --base main --title "EXP-002: Music Test Organizer"
   ```

3. **Efter merge, städa:**
   ```bash
   cd C:\Users\haege\Music
   git worktree remove .worktrees/002-music-test-organizer
   git branch -d experiment/002-music-test-organizer
   ```

## Session-logg

Loggad till: `C:\Users\haege\McClaw\overnight\logs\2026-02-24_EXP-002_Music_session.log`
