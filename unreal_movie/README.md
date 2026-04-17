# Buddy's Big Day — 3D Animated Kids Movie

A 30-second animated kids movie rendered with **Blender 4.x** via a fully automated Python script.
No clicks, no GUI — just run the script and get an MP4.

---

## Watch the movie

**[▶ Watch buddys_big_day.mp4](https://github.com/gge2898/Geremoah/blob/claude/unreal-kids-animation-SpB1W/unreal_movie/buddys_big_day.mp4)**

> GitHub renders `.mp4` files with a built-in video player — just click the link above.

---

## Story

| Time | Scene |
|------|-------|
| 0–5s | Camera pans across a bright, colorful meadow with trees and clouds |
| 5–15s | Buddy the orange ball rolls in from the left and starts bouncing |
| 15–22s | Five colorful balloons (red, blue, yellow, green, purple) float down from the sky |
| 22–30s | Buddy leaps up to join the balloons — everyone celebrates! |

---

## Run it yourself

### Requirements
- Blender 4.x (`sudo apt install blender` on Ubuntu)
- ffmpeg (`sudo apt install ffmpeg`)

### Steps

```bash
# 1. Render all 720 frames (640×360, 16 samples, ~12 min on 16 CPU cores)
blender --background --python Scripts/buddys_big_day.py

# 2. Assemble PNG frames into MP4
bash Scripts/assemble_mp4.sh /tmp/buddy_frames /tmp/buddys_big_day.mp4
```

The MP4 lands at `/tmp/buddys_big_day.mp4`.

---

## Technical details

| Property | Value |
|----------|-------|
| Render engine | Cycles (CPU) |
| Resolution | 640 × 360 |
| Frame rate | 24 fps |
| Duration | 30 seconds (720 frames) |
| Samples | 16 |
| Output | PNG sequence → H.264 MP4 via ffmpeg |

### Scene objects
- **Buddy** — orange `UVSphere` with Principled BSDF, two white eye spheres parented to it
- **8 trees** — cylinder trunk + two sphere canopy balls each
- **3 clouds** — groups of 3 flat-scaled spheres drifting slowly
- **5 balloons** — coloured spheres that float down and orbit during the finale
- **Sky** — Blender Nishita sky texture with sun at 40° elevation
- **Lighting** — single sun lamp at 4W + sky HDRI

All animation is driven by Bézier-interpolated keyframes set programmatically in `buddys_big_day.py`.
