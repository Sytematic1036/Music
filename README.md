# Music

Music generation and analysis tools.

## Experiments

See `experiments/` for ongoing experiments.

## Current: EXP-001 Relaxation Music Generator

Pipeline that:
1. Searches YouTube for popular relaxation music
2. Analyzes the music structure (tempo, key, patterns)
3. Generates new MIDI music based on analysis with variations

### Setup

```bash
pip install -r requirements.txt
```

### Usage

```bash
python main.py --search "relaxation music" --limit 3 --output generated.mid
```
