# EXP-003: Melody-Arrangement-Production Pipeline

## Status: EXPERIMENTAL

## Mål
Utveckla ett komplett musikskapande system med tre separata steg:
1. **Melodi** - Generera och optimera unika melodier
2. **Arrangemang** - Lägg till instrument-lager anpassade för genre
3. **Produktion** - Mix och master med genre-specifika inställningar

Varje steg ska vara lyssningsbart (preview) via:
- Browser-baserad player (Web Audio API)
- Python-player (pygame/fluidsynth)
- Export till WAV/MP3

Systemet ska lära sig vad som blir bra genom att spara parametrar i en vector-databas.

## Bygger på
- EXP-001 (relaxation-music-generator) - grundläggande MIDI-generering och analys

## Teknisk approach
- **Melodi:** Förbättrad melodigenerering med unikhets-optimering
- **Arrangemang:** Multi-track instrument layers med genre-profiles
- **Produktion:** Audio rendering med FluidSynth + effektkedja
- **Lärande:** SQLite + sqlite-vec för parameter-lagring och sökning
- **Player:** Tre metoder - browser, python, export

## Framgångskriterier
1. [ ] Melodigenerering producerar unika, lyssningsbara melodier
2. [ ] Arrangemang lägger till passande instrument-lager per genre
3. [ ] Produktion renderar till WAV/MP3 med godkänd ljudkvalitet
4. [ ] Alla tre uppspelningsmetoder fungerar
5. [ ] Vector DB sparar och kan söka bland parametrar
6. [ ] Alla tester passerar

## Skapad
2026-02-24

## Iteration
v1_autonomous_2026-02-24
