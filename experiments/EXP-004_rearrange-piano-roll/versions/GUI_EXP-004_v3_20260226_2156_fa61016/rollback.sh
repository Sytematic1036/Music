#!/bin/bash
# Rulla tillbaka till version: GUI_EXP-004_v3_20260226_2156_fa61016
# Skapad: 2026-02-26

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(dirname "$SCRIPT_DIR")/../iterations/v3_kollaborativ_2026-02-26"

echo "Rullar tillbaka till: GUI_EXP-004_v3_20260226_2156_fa61016"
cp "$SCRIPT_DIR"/*.py "$TARGET/"
echo "Klar! Starta om servern för att aktivera."
