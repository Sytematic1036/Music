# EXP-002: Music Test Organizer

## Status: EXPERIMENTAL

## Mål

1. Skapa ett menyträd/mappsystem för att organisera musiktester med löpnummer (test_001_, test_002_, etc.)
2. Implementera ett kategoriseringssystem för musik i undermappar baserat på:
   - Genre (ambient, piano, nature, electronic)
   - Tempo (slow <80 BPM, medium 80-120 BPM, fast >120 BPM)
   - Mood (calm, energetic, focus, melancholic)
   - Source (generated, youtube, original)

## Bygger på

- EXP-001 (relaxation-music-generator) - använder samma analyzer för tempo-detektering

## Skapad

2026-02-24

## Teknisk approach

### Python-moduler

- `src/organizer.py` - Huvudmodul för kategorisering och filhantering
- `tests/test_organizer.py` - pytest-tester

### Mappsystem

```
music_library/
├── by_genre/
│   ├── ambient/
│   ├── piano/
│   ├── nature/
│   └── electronic/
├── by_tempo/
│   ├── slow/
│   ├── medium/
│   └── fast/
├── by_mood/
│   ├── calm/
│   ├── energetic/
│   ├── focus/
│   └── melancholic/
└── by_source/
    ├── generated/
    ├── youtube/
    └── original/
```

### Test-löpnummer

```
tests/
├── test_001_directory_structure.py
├── test_002_categorization_logic.py
├── test_003_file_operations.py
├── test_004_tempo_detection.py
└── test_005_integration.py
```

## Framgångskriterier

1. [x] Mappsystemet skapas korrekt
2. [x] Kategorisering baserat på tempo fungerar
3. [x] Testfiler med löpnummer organiseras
4. [x] pytest-tester passerar
5. [x] Integration med befintlig analyzer

## Edge cases

1. Okänd tempo → default till "medium"
2. Fil utan extension → ignorera
3. Befintlig fil i mål → suffix med _1, _2, etc.
