# v1_autonom_2026-02-26

## Vad gjordes
Lade till Logic-style scrolling till piano roll-GUI:t.

### Nya funktioner (EXP-005)
1. **Vertikal scrollbar** - alltid synlig med `overflow: scroll`
2. **Horisontell scrollbar** - alltid synlig
3. **Ruler** - visar beat-markeringar (var 4:e beat)
4. **Klickbar ruler** - klicka för att hoppa till position
5. **Playhead-triangel** - visar nuvarande position i ruler
6. **Playhead-linje** - vertikal linje i piano roll
7. **Catch mode** - auto-scroll så playhead alltid syns under uppspelning

### Vad som INTE ändrades
- Ljudrendering (FluidSynth + production effects)
- Filhantering (find-midi API)
- Notredigering (drag-and-drop)
- Export-funktioner

### Tekniska detaljer
- Använder `overflow: scroll` istället för `auto` för alltid synliga scrollbars
- Scrollbar-styling med webkit-scrollbar CSS
- Ruler renderas på canvas med beat-markeringar
- Playhead uppdateras via `timeupdate` event på Audio-elementet
- Catch mode scrollar automatiskt när playhead går utanför synligt område

## Baserat på
- EXP-004 v3 (player_rearrange_v3.py)
- Scroll.md (lösningsdokumentation)

## Testat
- [ ] MIDI-laddning fungerar
- [ ] Scrollbars syns
- [ ] Ruler visas med beat-markeringar
- [ ] Klick i ruler flyttar playhead
- [ ] Playhead följer uppspelning
- [ ] Catch mode fungerar
