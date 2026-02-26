# Versionshistorik - EXP-004 Rearrange Piano Roll

| Version | Datum | Status | Beskrivning |
|---------|-------|--------|-------------|
| GUI_EXP-004_v3_20260226_2156_fa61016 | 2026-02-26 21:56 | FUNGERAR | Stämplad version, piano roll GUI |
| v3_production-quality_20260226_1224 | 2026-02-26 12:24 | FUNGERAR | FluidSynth + instrument fix, gain=1.5 |
| v2 (iteration) | 2026-02-25 | DEPRECATED | Audio-to-MIDI (dålig kvalitet) |
| v1 (iteration) | 2026-02-24 | DEPRECATED | Första version |

## Senaste stabila version
`versions/GUI_EXP-004_v3_20260226_2156_fa61016/`

## Huvudförbättringar i v3
- Original MIDI-filer istället för audio-konvertering
- FluidSynth + SoundFont rendering
- Produktionseffekter (EQ, compression, reverb)
- Bevarar GM instrument (inte bara piano)
- Fixad gain (1.5 istället för 5.0 = ingen clipping)
