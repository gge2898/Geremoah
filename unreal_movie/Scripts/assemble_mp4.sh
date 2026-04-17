#!/bin/bash
# Assembles rendered PNG frames into an MP4 using ffmpeg.
# Run this after buddys_big_day.py finishes rendering.
#
# Usage:
#   bash assemble_mp4.sh [frames_dir] [output.mp4]

FRAMES_DIR="${1:-/tmp/buddy_frames}"
OUTPUT="${2:-/tmp/buddys_big_day.mp4}"

FRAME_COUNT=$(ls "$FRAMES_DIR"/frame_*.png 2>/dev/null | wc -l)
echo "Found $FRAME_COUNT frames in $FRAMES_DIR"

if [ "$FRAME_COUNT" -lt 1 ]; then
  echo "ERROR: No frames found. Run buddys_big_day.py first."
  exit 1
fi

ffmpeg -y \
  -framerate 24 \
  -i "$FRAMES_DIR/frame_%04d.png" \
  -c:v libx264 \
  -preset fast \
  -crf 20 \
  -pix_fmt yuv420p \
  "$OUTPUT"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo "Done! $OUTPUT ($SIZE)"
