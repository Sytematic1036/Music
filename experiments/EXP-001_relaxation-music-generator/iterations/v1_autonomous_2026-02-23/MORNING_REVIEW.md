# Autonom körning 2026-02-23

## Repo
`Music` (https://github.com/Sytematic1036/Music)

## Status
[x] LYCKADES / [ ] DELVIS / [ ] MISSLYCKADES

## Branch
`experiment/001-relaxation-music-generator`

## Sammanfattning
- Skapade komplett pipeline för avslappningsmusik-generering
- 4 moduler: youtube_search, downloader, analyzer, generator
- 45 enhetstester (42 passed, 3 skipped)
- MIDI-generering fungerar och producerar giltiga filer

## Arkitektur

```
main.py                    # Entry point med CLI
src/
├── youtube_search.py      # Sök avslappningsmusik på YouTube
├── downloader.py          # Ladda ner audio med yt-dlp
├── analyzer.py            # Analysera med librosa (tempo, tonart, struktur)
├── generator.py           # Generera MIDI med midiutil
└── pipeline.py            # Koppla ihop allt
tests/
├── test_youtube_search.py
├── test_downloader.py
├── test_analyzer.py
├── test_generator.py
└── test_pipeline.py
```

## Nya filer
- `main.py` - CLI entry point
- `pytest.ini` - Pytest konfiguration
- `src/__init__.py`
- `src/youtube_search.py` - YouTube-sökning (VideoResult, search_relaxation_music)
- `src/downloader.py` - Audio-nedladdning (DownloadResult, download_audio)
- `src/analyzer.py` - Ljudanalys (MusicalFeatures, analyze_audio, estimate_key)
- `src/generator.py` - MIDI-generering (GenerationParams, generate_relaxation_midi)
- `src/pipeline.py` - Huvudpipeline (run_pipeline, PipelineResult)
- `tests/test_*.py` - 5 testfiler med 45 tester

## Tester
```
pytest: 42 passed, 3 skipped
- test_analyzer.py: 6 passed
- test_downloader.py: 4 passed, 1 skipped
- test_generator.py: 11 passed
- test_pipeline.py: 7 passed
- test_youtube_search.py: 14 passed, 2 skipped
```

Skippade tester: Kräver externa paket (youtube-search-python, yt-dlp) som inte var installerade.

## Funktionalitet

### YouTube-sökning
- Söker efter avslappningsmusik med anpassningsbara söktermer
- Filtrerar på videolängd (3-60 min default)
- Sorterar på visningar (mest populär först)
- Stödjer flera kategorier (meditation, sleep, calm piano, etc.)

### Audio-nedladdning
- Använder yt-dlp för robust nedladdning
- Konverterar till WAV för analys
- Stödjer tidsbegränsning (max duration)

### Ljudanalys
- Extraherar tempo (BPM) med beat tracking
- Estimerar tonart med Krumhansl-Schmuckler algoritm
- Beräknar MFCC (timbre), spektrala features
- Identifierar strukturella segment

### MIDI-generering
- Procedurell generation baserad på analyserade features
- Stödjer dur/moll, olika tempon
- Genererar melodi, ackord och bas
- Använder relaxation-specifika patterns (mjuka dynamiker, glesa melodier)
- Reproducerbar med seed för konsekventa resultat

## Användning

```bash
# Installera dependencies
pip install -r requirements.txt

# Kör med default (sök, ladda ner, analysera, generera)
python main.py --search "relaxation music" --limit 3 --output output/

# Snabbtest utan nedladdning (använder default-parametrar)
python main.py --no-download --duration 60 --output test_output/

# Generera flera variationer
python main.py --variations 3 --variation-amount 0.4
```

## Nästa steg för användaren

1. **Granska ändringar:**
   ```bash
   cd C:\Users\haege\Music
   git diff main...experiment/001-relaxation-music-generator
   ```

2. **Om OK, pusha och skapa PR:**
   ```bash
   cd .worktrees/001-relaxation-music-generator
   git push -u origin experiment/001-relaxation-music-generator
   gh pr create --base main --title "EXP-001: Relaxation Music Generator"
   ```

3. **Efter merge, städa:**
   ```bash
   cd C:\Users\haege\Music
   git worktree remove .worktrees/001-relaxation-music-generator
   git branch -d experiment/001-relaxation-music-generator
   ```

## Tekniska anteckningar

- Python 3.14 kompatibel
- Kräver: midiutil, numpy, (valfritt: librosa, youtube-search-python, yt-dlp)
- MIDI-filer kan öppnas i valfri DAW (GarageBand, FL Studio, Ableton, etc.)
- Analysmodulen kräver librosa + scipy för full funktionalitet
