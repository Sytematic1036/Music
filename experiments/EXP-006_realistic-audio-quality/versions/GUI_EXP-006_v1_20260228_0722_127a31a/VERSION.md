# GUI_EXP-006_v1_20260228_0722_127a31a

| Fält | Värde |
|------|-------|
| **Experiment** | EXP-006 Realistic Audio Quality |
| **Version** | v1 |
| **Datum** | 2026-02-28 07:22 |
| **Commit** | 127a31a |
| **Status** | VERIFIED |

## Ändringar

### Förbättrad reverb
- Bytt från `aecho` (eko-effekt) till multi-tap reverb
- Simulerar rum med flera reflektioner (30ms, 70ms, 120ms)
- Mer realistiskt rumsljud

### Server-side rendering
- GUI renderar nu via FluidSynth på servern
- Både GUI och produktion använder samma ljudmotor
- Identiskt ljud i Rearrange-fliken och exporterad produktion

### MIDI humanisering
- Velocity-variation (gaussian +-12)
- Gör MIDI mindre mekaniskt perfekt

## Filer

| Fil | Beskrivning |
|-----|-------------|
| `player_rearrange.py` | GUI med server-rendering |
| `production.py` | Förbättrad produktionsmodul |

## Test

12/12 Playwright-tester passerar.
