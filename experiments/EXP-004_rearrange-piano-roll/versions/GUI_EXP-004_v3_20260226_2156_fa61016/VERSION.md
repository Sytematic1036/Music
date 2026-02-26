# GUI_EXP-004_v3_20260226_2156_fa61016

## Metadata
- **Stämplad:** 2026-02-26 21:56
- **Git commit:** fa61016 - Merge pull request #9 from Sytematic1036/experiment/EXP-004-v3-production-quality
- **Experiment:** EXP-004_rearrange-piano-roll
- **Iteration:** v3_kollaborativ_2026-02-26
- **Status:** FUNGERAR

## Beskrivning
Piano roll GUI för att rearrangea MIDI-filer. Använder original MIDI-filer för perfekt kvalitet.

## Komponenter
### Frontend/Server
- `player_rearrange_v3.py` - Huvudserver med GUI (port 8765)
- `simple_server.py` - Enkel testserver
- `test_server.py` - Testserver

## Vad fungerar
- Piano roll med canvas-baserad rendering
- Drag-and-drop för att flytta noter (horisontellt = tid, vertikalt = tonhöjd)
- Ta bort noter
- Zoom och snap-kontroller
- Undo-funktion
- Export MIDI
- 29 Playwright-tester passerar

## Starta
```bash
cd experiments/EXP-004_rearrange-piano-roll/iterations/v3_kollaborativ_2026-02-26
python player_rearrange_v3.py
# Öppna http://localhost:8765
```

## Beroenden
- Python 3.x
- mido (MIDI-hantering)
- Webbläsare med JavaScript

## Rollback
```bash
./rollback.sh
```
