#!/usr/bin/env python3
"""
Relaxation Music Generator

Searches YouTube for popular relaxation music, analyzes the structure,
and generates new MIDI music based on the analysis with variations.

Usage:
    python main.py --search "relaxation music" --limit 3 --output output/
    python main.py --no-download --duration 60  # Quick test without downloading
"""

from src.pipeline import main

if __name__ == "__main__":
    exit(main())
