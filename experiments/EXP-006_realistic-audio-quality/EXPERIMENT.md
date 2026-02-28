# EXP-006: Realistic Audio Quality

| Fält | Värde |
|------|-------|
| **Status** | EXPERIMENTAL |
| **Ramverk** | Python + FluidSynth + FFmpeg |
| **Bygger från** | src/production.py |
| **Datum** | 2026-02-28 |
| **Iteration** | v1_initial |

## Mål
Förbättra ljudkvaliteten i produktionen så att den låter mer realistisk och mindre digital/synthig.

## Problem att lösa
1. FluidR3_GM SoundFont är generisk - saknar instrument-specifik kvalitet
2. Reverb via `aecho` är primitiv echo-effekt, inte äkta rumsklang
3. Ingen humanisering av MIDI (perfekt mekaniskt)
4. Begränsad dynamik (velocity layers)

## Lösningar att testa
1. **Bättre reverb** - Byt från aecho till convolve/afir (impulse response)
2. **Humanisering** - Timing/velocity-variation i MIDI
3. **Bättre SoundFonts** - Testa VSCO, SSO eller liknande
4. **Layering** - Kombinera flera SoundFonts för rikare ljud

## Testfil
`C:\Users\haege\Kod\Music\output_2026-02-26_1034\02_arrangement.mid`

## Iterationer
| Version | Typ | Datum | Beskrivning |
|---------|-----|-------|-------------|
| v1_initial | Autonom | 2026-02-28 | Initial implementation med förbättrad reverb och humanisering |
