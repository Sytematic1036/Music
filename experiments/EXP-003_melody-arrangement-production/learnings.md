# Learnings - EXP-003

## Vad fungerade

### Melody Module
- **Contour-baserad generering** - Arch, descending, wave patterns ger naturliga melodier
- **Motif development** - Transponering, inversion, augmentation skapar variation
- **Uniqueness optimization** - Pattern detection med hash + simulated annealing fungerar

### Arrangement Module
- **Genre-specifika instrument** - Fördefinierade instrument-paletter per genre
- **Pan/volume balans** - ROLE_PAN och ROLE_VOLUME dictionaries förenklar mixing
- **Counter-melody** - Contrary motion skapar intressant rörelse

### Learning Module
- **Vector embeddings** - 16-dimensionella vektorer fångar musikaliska parametrar
- **Cosine similarity** - Fungerar bra för att hitta liknande generationer
- **SQLite + struct** - Blob-lagring för vektorer är snabbt och enkelt

### Player Module
- **Browser-baserad** - Tone.js + @tonejs/midi hanterar MIDI i browser
- **Drag-and-drop** - Enkelt UX för att lyssna på olika steg
- **Fallback-kedja** - Browser → Python → Export

## Vad INTE fungerade

### Enum serialization
- **Problem:** `asdict()` konverterar inte Enums till strings
- **Lösning:** Skapade `_serialize_dataclass()` som hanterar Enum.value

### FluidSynth integration
- **Problem:** Inte installerat i test-miljön
- **Lösning:** Gjorde tester som kräver FluidSynth skipable med `@pytest.mark.skipif`

### Time signature tuple
- **Problem:** Tuples serialiseras inte till JSON
- **Lösning:** Konverterade till list i `_serialize_dataclass()`

## Tekniska insikter

### Best practices för melodigenerering
1. **Contour är viktigt** - Melodier behöver tydlig riktning
2. **Motifs skapar struktur** - 4-8 noter som utvecklas
3. **Sparsitet för lugnt** - Relaxation = färre noter

### Best practices för arrangemang
1. **Frequency separation** - Bass center, texture left/right
2. **Dynamics** - Pads mjuka (vol 45-60), melody starkare (80-100)
3. **Genre profiles** - Instrument-val per genre viktigare än processing

### Best practices för vector DB
1. **Normalisera** - Alla dimensioner 0-1
2. **Fixed dimensions** - 16 räcker för musikaliska parametrar
3. **Genre one-hot** - Snabbare än textembeddings

## Framtida förbättringar

1. **Transformer-baserad melodi** - Träna på befintliga melodier
2. **Audio analysis feedback** - Analysera rendered audio för kvalitet
3. **Real-time preview** - WebSocket för streaming preview
4. **GPU acceleration** - FluidSynth med CUDA för snabbare rendering
