# v3_production-quality_20260226_1224

## Metadata
- **Stämplad:** 2026-02-26 12:24
- **Git base:** c40c707 (main)
- **Experiment:** EXP-004_rearrange-piano-roll
- **Iteration:** v3_kollaborativ_2026-02-26
- **Status:** FUNGERAR

## Beskrivning
Version 3 av Rearrange Piano Roll Editor med produktionskvalitet.

### Huvudförbättringar från v2:
1. **Original MIDI-filer** - Använder original MIDI istället för audio-to-MIDI konvertering
2. **FluidSynth rendering** - Riktig SoundFont-baserad rendering (FluidR3_GM.sf2)
3. **Produktionseffekter** - Samma EQ, compression, reverb som production.py
4. **Instrument bevaras** - GM program numbers kopieras korrekt (inte bara piano)
5. **Gain-fix** - Ändrat från gain=5.0 (clipping) till gain=1.5

## Komponenter

### player_rearrange_v3.py (huvudfil)
- HTTP server på port 8765
- Piano roll editor i browser
- FluidSynth + FFmpeg rendering pipeline
- API endpoints: `/api/find-midi`, `/api/render`

### Viktiga funktioner:
- `apply_production_effects()` - Samma effektkedja som production.py
- `midi_to_audio()` - FluidSynth rendering med gain=1.5
- `loadMidiFromTonejs()` - Bevarar instrument (track.instrument.number)
- `startPlayback()` - Bygger MIDI med korrekta instrument

## Ändringar i denna version

### Fixade buggar:
1. **Clipping/brus** - gain=5.0 → gain=1.5 i FluidSynth
2. **Alla instrument = piano** - Nu bevaras GM program numbers
3. **Server timeout** - ThreadingMixIn för concurrent requests
4. **MIDI parsing error** - Fixade corrupt 02_arrangement.mid

### Effektkedja (RELAXATION preset):
```
volume=0.8
lowshelf=f=200:g=-2.0      (bass)
equalizer=f=1000:g=1.0     (mid)
highshelf=f=3000:g=2.0     (treble)
acompressor=-12dB:4:1
aecho=0.8:0.9:150:0.25     (reverb)
stereotools=mlev=1.1       (stereo width)
alimiter=0.95
```

## Testresultat
- MIDI loading: OK (7 tracks, 219 notes)
- FluidSynth rendering: OK (64.5s audio från 59.4s MIDI)
- Volym: -21.6 dB mean, -8.5 dB max (ingen clipping)
- Instrument: Alla 6 GM programs bevaras

## Beroenden
- Python 3.10+
- FluidSynth (`choco install fluidsynth`)
- FFmpeg (`choco install ffmpeg`)
- SoundFont: C:/soundfonts/FluidR3_GM.sf2 (148 MB)

## Användning
```bash
cd experiments/EXP-004_rearrange-piano-roll/versions/v3_production-quality_20260226_1224
python player_rearrange_v3.py
# Öppna http://localhost:8765
```

## Relaterade filer
- `src/production.py` - Ändrad gain=5.0 → gain=1.5
- `output_2026-02-26_1034/` - Ny pipeline-körning med korrekt gain
