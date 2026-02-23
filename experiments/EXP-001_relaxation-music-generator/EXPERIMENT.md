# EXP-001: Relaxation Music Generator

## Status: EXPERIMENTAL

## Mål
Skapa en pipeline som:
1. Hittar populär avslappningsmusik på YouTube
2. Analyserar hur musiken är uppbyggd (tempo, tonart, struktur)
3. Genererar egen MIDI-musik baserad på analysen med egna variationer

## Bygger på
- Inget (första experimentet i repot)

## Teknisk approach
- **YouTube-sökning:** ytmusicapi eller youtube-search-python
- **Nedladdning:** yt-dlp
- **Ljudanalys:** librosa (tempo, MFCC, spektral analys)
- **Musikgenerering:** midiutil (procedurell MIDI-generation)

## Framgångskriterier
1. [ ] Kan söka och hitta avslappningsmusik på YouTube
2. [ ] Kan ladda ner audio för analys
3. [ ] Kan extrahera tempo, tonart och struktur från ljud
4. [ ] Kan generera MIDI-musik med variationer baserat på analys
5. [ ] Alla tester passerar

## Skapad
2026-02-23
