# Versionshistorik - EXP-004 Rearrange Piano Roll

| Version | Datum | Status | Beskrivning |
|---------|-------|--------|-------------|
| v3_production-quality_20260226_1224 | 2026-02-26 12:24 | FUNGERAR | FluidSynth + instrument fix, gain=1.5 |
| v2 (iteration) | 2026-02-25 | DEPRECATED | Audio-to-MIDI (dålig kvalitet) |
| v1 (iteration) | 2026-02-24 | DEPRECATED | Första version |

## Senaste stabila version
`versions/v3_production-quality_20260226_1224/`

## Huvudförbättringar i v3
- Original MIDI-filer istället för audio-konvertering
- FluidSynth + SoundFont rendering
- Produktionseffekter (EQ, compression, reverb)
- Bevarar GM instrument (inte bara piano)
- Fixad gain (1.5 istället för 5.0 = ingen clipping)
