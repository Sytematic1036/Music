# Learnings - EXP-004: Rearrange Piano Roll

## Vad fungerade

1. **Canvas-baserad rendering** - Snabb och flexibel, kan hantera många noter
2. **Tone.js/@tonejs/midi** - Utmärkt för MIDI-parsning och export i browser
3. **Playwright för GUI-testning** - Automatiserade tester som verkligen klickar och drar
4. **Tab-baserad navigation** - Behåller befintlig player-funktionalitet intakt
5. **Snap-kvantisering** - Gör det enkelt att placera noter på rätt beats

## Vad fungerade INTE

1. **Binär MIDI i tester** - Handkodad MIDI-data parsades inte korrekt av Tone.js. Lösning: Använd midiutil för att generera testfiler, eller gör testerna mer toleranta.
2. **Regex i Playwright/Python** - JavaScript-syntax `/pattern/` fungerar inte i Python. Måste använda `re.compile(r"pattern")`.

## Tekniska insikter

1. **Note-koordinatsystem:**
   - X = `startTime * pixelsPerBeat`
   - Y = `(maxPitch - pitch) * noteHeight`
   - Detta gör att högre toner är högre upp (intuitivt)

2. **Drag-and-drop komplexitet:**
   - Måste spara originalposition vid mousedown
   - Beräkna delta från startposition, inte senaste position
   - Snap ska appliceras på nya koordinater, inte delta

3. **MIDI export via Blob:**
   ```javascript
   const blob = new Blob([midi.toArray()], { type: 'audio/midi' });
   const url = URL.createObjectURL(blob);
   // ... trigger download
   URL.revokeObjectURL(url);  // Städa upp
   ```

4. **History/Undo:**
   - JSON.stringify/parse för deep copy
   - Max history-längd för minneshantering

## Rekommendationer för framtida arbete

1. **Velocity-editing** - Använd not-höjd eller färgintensitet för velocity
2. **Multi-select** - Shift-klick för att välja flera noter, flytta alla samtidigt
3. **Playhead** - Visa uppspelningsposition som vertikal linje
4. **Keyboard shortcuts** - Ctrl+C/V för copy/paste, arrow keys för finpositionering
5. **Touch support** - För tablets, behöver touch events utöver mouse events
