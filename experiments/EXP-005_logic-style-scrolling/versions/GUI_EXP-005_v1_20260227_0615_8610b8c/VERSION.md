# GUI_EXP-005_v1_20260227_0615_8610b8c

## Metadata
- **Stämplad:** 2026-02-27 06:15
- **Git commit:** 8610b8c
- **Experiment:** EXP-005_logic-style-scrolling
- **Iteration:** v1_autonom_2026-02-26
- **Status:** FUNGERAR

## Beskrivning
Logic-style scrolling för piano roll-GUI. Lägger till scrollbars, ruler och playhead utan att ändra ljud eller filhantering.

## Komponenter
- `player_scrolling.py` - Huvudserver med GUI (port 8765)

## Nya funktioner (EXP-005)
- Vertikal scrollbar (alltid synlig)
- Horisontell scrollbar (alltid synlig)
- Ruler med beat-markeringar
- Klickbar ruler för att hoppa i tid
- Playhead-triangel i ruler
- Playhead-linje i piano roll
- Catch mode (auto-scroll vid uppspelning)

## Vad som INTE ändrades
- Ljudrendering (FluidSynth + production effects)
- Filhantering (find-midi API)
- Notredigering (drag-and-drop)
- Export-funktioner

## Bygger på
- EXP-004 v3 (player_rearrange_v3.py)
- Scroll.md (lösningsdokumentation)

## Starta
```bash
cd experiments/EXP-005_logic-style-scrolling/iterations/v1_autonom_2026-02-26/src
python player_scrolling.py
# Öppna http://localhost:8765
```

## Beroenden
- Python 3.x
- FluidSynth + SoundFont
- mido, ffmpeg

## Rollback
```bash
./rollback.sh
```
