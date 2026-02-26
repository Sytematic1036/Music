# Autonom Körning 2026-02-26 - EXP-004 v2

## Status
[x] LYCKADES

## Target Repository
- **Repo:** Music
- **GitHub:** https://github.com/Sytematic1036/Music
- **Target experiment-ID:** EXP-004 (v2 iteration)

## Sammanfattning

Implementerade fullständigt workflow för att:
1. **Öppna MP3/WAV-filer** och konvertera till MIDI-noter automatiskt
2. **Visa noter i Logic-liknande piano roll** med separata tracks (Melody, Bass, Harmony)
3. **Redigera noter** (drag-and-drop för tid/tonhöjd, högerklick för radering)
4. **Lyssna på ändringar** via Tone.js synth playback
5. **Spara till MP3/WAV** via FluidSynth + SoundFont

## Testresultat

```
================================ TEST RESULTS ================================
17 passed, 1 skipped, 23 warnings in 268.22s (0:04:28)

Passerade tester:
  ✅ Tab navigation (3 tester)
  ✅ Audio conversion (2 tester)
  ✅ Note editing (4 tester)
  ✅ Playback controls (1 test)
  ✅ Export functionality (2 tester)
  ✅ Track controls (2 tester)
  ✅ Clear function (1 test)
  ✅ Full workflow (1 test)

Fullständigt workflow-test:
  ✅ Laddade: production.mp3
  ✅ Detekterade: 368 noter (106 melody, 8 bass, 254 harmony)
  ✅ Tempo: 129.2 BPM
  ✅ Raderade: 10 noter (368 → 358)
  ✅ Sparade MIDI: 3190 bytes
  ✅ Renderade WAV: 10.6 MB
```

## Nya funktioner i v2

### 1. Audio-to-MIDI konvertering
- Använder **librosa** för pitch detection
- Separerar ljud i **Melody**, **Bass** och **Harmony** tracks
- Detekterar tempo automatiskt

### 2. Logic-liknande track-vy
- Färgkodade tracks (röd=melody, blå=bass, grön=harmony)
- **Mute/Solo**-knappar per track
- Track-visibilitet toggle

### 3. Playback i Rearrange-fliken
- **Play/Pause/Stop**-knappar
- Playhead-indikator på canvas
- Tone.js synth för realtids-preview

### 4. Spara-funktion
- **Save Audio**-knapp öppnar dialog
- Välj mellan **WAV** (okomprimerad) och **MP3** (komprimerad)
- Använder **FluidSynth** med **FluidR3_GM** SoundFont

### 5. Förbättrad piano roll
- Visa noter från MP3/WAV-filer
- Zoom X/Y kontroller
- Snap-kvantisering (1/16, 1/8, 1/4)
- Undo med Ctrl+Z
- Status-bar med not-antal och tempo

## Filer i denna iteration

| Fil | Storlek | Beskrivning |
|-----|---------|-------------|
| `audio_to_midi.py` | 14 KB | Backend för audio→MIDI konvertering |
| `player_rearrange_v2.py` | 75 KB | HTTP-server + HTML/JS player |
| `test_rearrange_v2.py` | 22 KB | Playwright-tester (17 stycken) |
| `output/rearranged_test.wav` | 10.6 MB | Testad output-fil |

## Beroenden

### Python
- `librosa>=0.11.0` (audio analysis)
- `midiutil>=1.2.1` (MIDI generation)
- `numpy>=2.0.0` (numerics)
- `playwright>=1.40.0` (testing, optional)

### System
- **FluidSynth** (för MIDI→audio rendering)
- **SoundFont** (FluidR3_GM.sf2, 142MB)

### JavaScript (CDN)
- Tone.js v14 (synth + MIDI playback)
- @tonejs/midi v2 (MIDI parsing)

## PR-instruktioner

### 1. Skapa branch i Music repo
```bash
cd C:/Users/haege/Kod/Music
git checkout main
git pull origin main
git checkout -b experiment/004-rearrange-v2-audio
```

### 2. Kopiera filer
```bash
# Skapa v2 iteration-mapp
mkdir -p experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26

# Kopiera källfiler
cp experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/audio_to_midi.py \
   experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/

cp experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/player_rearrange_v2.py \
   experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/

cp experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/test_rearrange_v2.py \
   experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/

cp experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/MORNING_REVIEW.md \
   experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/
```

### 3. Uppdatera requirements.txt (om nödvändigt)
```bash
# Kolla om librosa redan finns
grep -q "librosa" requirements.txt || echo "librosa>=0.11.0" >> requirements.txt
```

### 4. Commit och push
```bash
git add experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26/
git commit -m "feat(EXP-004): add v2 with audio-to-MIDI support

New features:
- Load MP3/WAV files and convert to MIDI for editing
- Logic-like track view with Melody/Bass/Harmony separation
- Playback edited notes with Tone.js synth
- Save Audio button to export as WAV/MP3 via FluidSynth

Test results:
- 17 Playwright tests passing
- Full workflow verified with production.mp3

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push -u origin experiment/004-rearrange-v2-audio
```

### 5. Skapa PR
```bash
gh pr create --base main --title "EXP-004 v2: Audio-to-MIDI Rearrange" --body "$(cat <<'EOF'
## Summary
- Adds audio-to-MIDI conversion for MP3/WAV files
- Logic-like track view with Melody, Bass, Harmony separation
- Save Audio button to export edited arrangement as WAV/MP3

## New Features
- **Audio import:** Drop MP3/WAV, auto-converts to editable MIDI
- **Track separation:** Melody (red), Bass (blue), Harmony (green)
- **Playback:** Preview edits with Tone.js synth
- **Export:** Save as WAV (FluidSynth) or MP3 (ffmpeg)

## Test plan
- [x] 17 Playwright tests passing
- [x] Full workflow tested with production.mp3
- [x] WAV export verified (10.6 MB output)
- [ ] Manual verification in browser

## Dependencies
- librosa (audio analysis)
- FluidSynth + SoundFont (MIDI→audio)

🤖 Generated with Claude Code
EOF
)"
```

## Användning

### Starta servern
```bash
cd C:/Users/haege/Kod/Music/experiments/EXP-004_rearrange-piano-roll/iterations/v2_autonomous_2026-02-26
python player_rearrange_v2.py
```

### Öppna i browser
```
http://localhost:8765/player.html
```

### Workflow
1. Klicka på **Rearrange**-fliken
2. Dra och släpp en MP3/WAV-fil (vänta på konvertering)
3. Redigera noter i piano roll
4. Klicka **Play** för att förhandsgranska
5. Klicka **Save Audio** för att exportera

## Begränsningar

1. **Audio-to-MIDI kvalitet:** Librosa pitch detection är bättre för monofoni än polyfoni. För komplex musik kan resultatet vara approximativt.

2. **FluidSynth krävs:** MIDI→audio export kräver FluidSynth + SoundFont. Utan dessa kan endast MIDI exporteras.

3. **Python 3.14:** basic-pitch (bättre ML-baserad transkribering) stöder inte Python 3.14 ännu. Använder librosa som fallback.

## Nästa steg (förslag)

1. **Note creation:** Dubbelklicka för att skapa nya noter
2. **Multi-select:** Shift-klick för att välja flera noter
3. **Copy/paste:** Ctrl+C/V för noter
4. **Velocity editing:** Visa/ändra velocity per not
5. **Better audio-to-MIDI:** Integrera basic-pitch när Python 3.14 stöds
