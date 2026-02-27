# EXP-005: Logic-Style Scrolling

## Status: EXPERIMENTAL

## Bygger från
EXP-004_rearrange-piano-roll (v3_kollaborativ_2026-02-26)

## Mål
Lägga till Logic Pro-liknande scrolling och playhead till piano roll-GUI:t.

**VIKTIGT:** Ändrar ENDAST scrolling/playhead. Ändrar INTE:
- Ljudrendering (FluidSynth)
- Filhantering
- Notredigering
- Något annat

## Funktioner att lägga till
1. Vertikal scrollbar (alltid synlig)
2. Horisontell scrollbar (alltid synlig)
3. Ruler med beat-markeringar
4. Klickbar ruler för att hoppa i tid
5. Playhead-triangel som visar position
6. Auto-scroll (catch mode) när musik spelas

## Teknisk approach
- Använd `overflow: scroll` (inte auto)
- UMD-version av @tonejs/midi: `unpkg.com/@tonejs/midi`
- Playhead som CSS-element med absolute positioning
- Ruler med canvas för beat-markeringar

## Framgångskriterier
1. [ ] MIDI-laddning fungerar fortfarande (regression test)
2. [ ] Vertikal scrollbar synlig
3. [ ] Horisontell scrollbar synlig
4. [ ] Ruler med beat-markeringar
5. [ ] Klick i ruler flyttar playhead
6. [ ] Playhead-triangel visar position
7. [ ] Auto-scroll följer playhead vid uppspelning

## Skapad
2026-02-26

## Iteration
v1_autonom_2026-02-26
