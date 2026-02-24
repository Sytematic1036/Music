# EXP-001: Relaxation Music Generator

## Status: VERIFIED

## Mål
Skapa en pipeline som:
1. Hittar populär avslappningsmusik på YouTube
2. Analyserar hur musiken är uppbyggd (tempo, tonart, struktur)
3. Genererar egen MIDI-musik baserad på analysen med egna variationer

## Bygger på
- Inget (första experimentet i repot)

## Teknisk approach
- **YouTube-sökning:** youtube-search-python
- **Nedladdning:** yt-dlp
- **Ljudanalys:** librosa (tempo, MFCC, spektral analys, Krumhansl-Schmuckler key detection)
- **Musikgenerering:** midiutil (procedurell MIDI-generation)

## Framgångskriterier
1. [x] Kan söka och hitta avslappningsmusik på YouTube
2. [x] Kan ladda ner audio för analys
3. [x] Kan extrahera tempo, tonart och struktur från ljud
4. [x] Kan generera MIDI-musik med variationer baserat på analys
5. [x] Alla tester passerar (42 passed, 3 skipped)

## Resultat
- Komplett pipeline implementerad
- 4 moduler: youtube_search, downloader, analyzer, generator
- 45 enhetstester
- MIDI-generering verifierad

## Skapad
2026-02-23

## Iteration
v1_autonomous_2026-02-23
