# Autonom Körning 2026-02-25

## Status
[x] LYCKADES

## Target Repository
- **Repo:** Music
- **GitHub:** https://github.com/Sytematic1036/Music
- **Target experiment-ID:** EXP-004

## Sammanfattning
- Skapade "Rearrange"-flik med canvas-baserad piano roll
- Implementerade drag-and-drop för noter (tid och tonhöjd)
- Implementerade notborttagning (högerklick/Delete)
- Alla 28 tester passerar (16 enhetstester + 12 Playwright GUI-tester)

## Funktionalitet

### Rearrange-tab
- **Canvas-baserad piano roll** med horisontell tid och vertikal tonhöjd
- **Pianotangenter** på vänster sida (C2-C7)
- **Drag-and-drop** för att flytta noter:
  - Horisontellt = ändra tid
  - Vertikalt = ändra tonhöjd
- **Ta bort noter** med högerklick eller Delete-tangent
- **Zoom-kontroller** för horisontell och vertikal skala
- **Snap-inställning** för kvantisering (1/16, 1/8, 1/4)
- **Undo** med Ctrl+Z
- **Export MIDI** med modifierade noter
- **Track-lista** med färgkodade spår
- **Status-bar** med not-antal och cursor-position

### Befintlig Player-tab
- Bevarad exakt som original
- Stage-indikatorer (Melody, Arrangement, Production)
- Drag-drop filuppladdning
- Play/Pause/Stop
- Volymkontroll

## Testresultat

```
============================= 28 passed in 49.80s =============================

Unit tests: 16 passed
- Module import
- HTML structure
- JavaScript logic
- CSS styles

Playwright GUI tests: 12 passed
- Tab navigation
- Element visibility
- Canvas rendering
- Zoom controls
- Snap settings
- Drag-and-drop
- Note deletion
```

## Filer i detta experiment

### Nya filer
| Fil | Beskrivning |
|-----|-------------|
| `src/player_rearrange.py` | Utökad player med Rearrange-tab |
| `tests/test_rearrange_unit.py` | Enhetstester |
| `tests/test_rearrange_playwright.py` | GUI-tester med Playwright |

### Fixture-filer (för referens)
| Fil | Beskrivning |
|-----|-------------|
| `fixtures/player_original.py` | Original player.py från Music repo |
| `fixtures/melody_original.py` | Original melody.py med MelodyNote |

## Manuella steg för PR

### 1. Skapa experiment-mapp i Music
```bash
cd C:/Users/haege/Music
mkdir -p experiments/EXP-004_rearrange-piano-roll/{src,tests,fixtures,failures,iterations/v1_autonomous_2026-02-25}
```

### 2. Kopiera filer
```bash
# Kopiera källkod
cp "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll/src/player_rearrange.py" \
   "C:/Users/haege/Music/experiments/EXP-004_rearrange-piano-roll/src/"

# Kopiera tester
cp "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll/tests/"*.py \
   "C:/Users/haege/Music/experiments/EXP-004_rearrange-piano-roll/tests/"

# Kopiera EXPERIMENT.md
cp "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll/EXPERIMENT.md" \
   "C:/Users/haege/Music/experiments/EXP-004_rearrange-piano-roll/"

# Kopiera success_criteria.yaml
cp "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll/fixtures/success_criteria.yaml" \
   "C:/Users/haege/Music/experiments/EXP-004_rearrange-piano-roll/fixtures/"

# Kopiera MORNING_REVIEW
cp "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll/iterations/v1_autonomous_2026-02-25/MORNING_REVIEW.md" \
   "C:/Users/haege/Music/experiments/EXP-004_rearrange-piano-roll/iterations/v1_autonomous_2026-02-25/"
```

### 3. Skapa EXPERIMENT.md i Music
```markdown
# EXP-004: Rearrange Piano Roll

## Status: EXPERIMENTAL

## Bygger från
EXP-003

## Mål
Canvas-baserad piano roll för att rearrangera noter visuellt.

## Framgångskriterier
1. [x] Rearrange-flik visas
2. [x] Noter renderas på canvas
3. [x] Kan flytta noter i tid (horisontellt)
4. [x] Kan flytta noter i tonhöjd (vertikalt)
5. [x] Kan ta bort noter
6. [x] Playwright-tester passerar

## Skapad
2026-02-25
```

### 4. Skapa branch och PR
```bash
cd C:/Users/haege/Music
git checkout -b experiment/004-rearrange-piano-roll
git add experiments/EXP-004_rearrange-piano-roll
git commit -m "feat(EXP-004): add rearrange piano roll tab

- Canvas-based piano roll editor
- Drag notes to change time (horizontal)
- Drag notes to change pitch (vertical)
- Delete notes with right-click or Delete key
- 28 tests passing (unit + Playwright)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push -u origin experiment/004-rearrange-piano-roll
gh pr create --base main --title "EXP-004: Rearrange Piano Roll" --body "$(cat <<'EOF'
## Summary
- Adds 'Rearrange' tab to the browser player with canvas-based piano roll
- Notes can be dragged to change time (horizontal) or pitch (vertical)
- Notes can be deleted with right-click or Delete key
- Export modified MIDI

## Test plan
- [x] Unit tests: 16 passed
- [x] Playwright GUI tests: 12 passed
- [ ] Manual verification in browser

## Screenshots
_Add screenshots of the Rearrange tab_

Generated with Claude Code
EOF
)"
```

### 5. Städa McClaw (efter PR är mergad)
```bash
rm -rf "C:/Users/haege/McClaw/experiments/EXP-004_for_Music_rearrange-piano-roll"
```

## Integration med befintlig player.py

För att integrera med den befintliga `src/player.py`:

### Option A: Ersätt HTML-template
Ersätt `BROWSER_PLAYER_HTML` i `player.py` med `BROWSER_PLAYER_WITH_REARRANGE_HTML` från `player_rearrange.py`.

### Option B: Separat modul
Behåll `player_rearrange.py` som separat modul och importera vid behov:
```python
from experiments.EXP004.src.player_rearrange import play_with_rearrange
```

## Arkitekturnoteringar

### Note-representation
Använder samma format som `MelodyNote` från `melody.py`:
```javascript
{
    pitch: int,        // MIDI 0-127
    startTime: float,  // I beats
    duration: float,   // I beats
    velocity: int      // 0-127
}
```

### Track-hantering
Spår hanteras med färgkodning:
- Melody: Röd (#e94560)
- Harmony: Grön (#4ade80)
- Bass: Blå (#60a5fa)
- etc.

### Beroenden
- Tone.js (MIDI-uppspelning)
- @tonejs/midi (MIDI-parsning/export)
- Playwright (GUI-testning, endast för test)

## Nästa steg (förslag)
1. Lägga till not-skapande (klick för att lägga till ny not)
2. Multi-select (markera flera noter samtidigt)
3. Copy/paste av noter
4. Playhead som visar nuvarande position vid uppspelning
5. Velocity-editing (höjd på noter = velocity)
