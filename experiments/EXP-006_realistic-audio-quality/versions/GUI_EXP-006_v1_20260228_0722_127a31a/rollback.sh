#!/bin/bash
# Rollback to GUI_EXP-006_v1_20260228_0722_127a31a
git checkout 127a31a -- experiments/EXP-006_realistic-audio-quality/iterations/v1_initial/src/
echo "Rolled back to GUI_EXP-006_v1_20260228_0722_127a31a"
