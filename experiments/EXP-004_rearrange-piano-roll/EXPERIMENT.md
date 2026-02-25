# EXP-004: Rearrange Piano Roll

## Status: EXPERIMENTAL

## Bygger från
EXP-003 (melody-arrangement-production)

## Mål
Skapa en "Rearrange"-flik i den befintliga browser-playern med en canvas-baserad piano roll där användaren kan:
1. Se alla noter från laddad MIDI/arrangement
2. Flytta noter i tid (horisontellt)
3. Flytta noter i tonhöjd (vertikalt)
4. Ta bort noter (högerklick eller delete)

## Teknisk approach
- Utöka befintlig `player.py` browser-player
- HTML5 Canvas för piano roll-rendering
- JavaScript för drag-and-drop interaktion
- Samma arkitektur som befintlig player (localhost:8765)

## Framgångskriterier
1. [x] "Rearrange"-flik visas i playern
2. [x] Noter från laddad fil visas i piano roll
3. [x] Kan flytta noter i tid genom att dra horisontellt
4. [x] Kan flytta noter i tonhöjd genom att dra vertikalt
5. [x] Kan ta bort noter
6. [x] Playwright-tester passerar (29 tester)

## Funktioner
- **Player-flik:** Play/Stop/Clear för MIDI/WAV/MP3
- **Rearrange-flik:** Canvas-baserad piano roll
- Klicka i drop-zone för att välja fil
- Drag-and-drop noter
- Zoom och snap-kontroller
- Undo och Export MIDI

## Edge cases
1. [x] Tom fil → Visar tom piano roll med grid
2. [x] Scroll/zoom fungerar
3. [x] Överlappande noter → Hanteras korrekt

## Skapad
2026-02-25
