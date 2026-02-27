#!/bin/bash
# Rulla tillbaka till version: GUI_EXP-005_v1_20260227_0615_8610b8c
# Skapad: 2026-02-27

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(dirname "$SCRIPT_DIR")/../iterations/v1_autonom_2026-02-26/src"

echo "Rullar tillbaka till: GUI_EXP-005_v1_20260227_0615_8610b8c"
cp "$SCRIPT_DIR"/*.py "$TARGET/"
echo "Klar! Starta om servern för att aktivera."
