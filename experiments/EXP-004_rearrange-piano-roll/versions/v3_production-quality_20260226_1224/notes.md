# Iteration v3 - Kollaborativ

**Datum:** 2026-02-26
**Typ:** Kollaborativ (användare + Claude)
**Baserad på:** v2_autonomous_2026-02-26

## Problem med v2

v2 använde **audio-to-MIDI konvertering** (librosa pitch detection) när MP3/WAV öppnades. Detta gav:
- Dålig ljudkvalitet (approximerade noter)
- Förlorad information (polyfoni förenklades)
- "Banalt" ljud jämfört med original

## Lösning i v3

Istället för att konvertera audio → MIDI, **använd original MIDI-filer** som skapade ljudfilen:

```
output_new/
├── 01_melody.mid       ← Original melodi
├── 02_arrangement.mid  ← Original arrangement (flerspår)
└── 03_production/
    ├── production.mp3  ← Genererad från MIDI
    └── production.wav
```

### Ny logik

1. När användaren öppnar `production.mp3`:
   - Sök efter `02_arrangement.mid` i parent-mapp
   - Eller `01_melody.mid` som fallback
2. Ladda MIDI-filen direkt (ingen konvertering)
3. Visa noter i piano roll med full kvalitet
4. Playback använder samma Tone.js synth som Player-fliken

### Fallback

Om ingen MIDI hittas:
- Visa dialog: "Ingen MIDI-fil hittades. Vill du söka manuellt?"
- Låt användaren välja MIDI-fil
- ELLER använd audio-to-MIDI som sista utväg (med varning)

## Ändringar från v2

- [x] `find_source_midi()` - Sök efter original MIDI
- [x] Uppdaterad `loadFile()` i JavaScript
- [x] Dialog för manuell MIDI-val
- [x] Samma Tone.js synth som Player
- [x] Tog bort automatisk audio-to-MIDI konvertering

## Mål

Ljudkvalitet i Rearrange ska vara **identisk** med Player-fliken.
