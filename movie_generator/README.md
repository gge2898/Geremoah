# AI Movie Generator

Describe any movie in plain English → ChatGPT writes a complete Blender Python script → Blender renders it with the fast **Eevee** real-time engine → your **MP4** lands in `output/`.

```
You: "a 10-second space battle with two ships firing lasers at each other"
 │
 ▼
ChatGPT  →  Blender Python script (bpy)
                     │
                     ▼
              Blender (Eevee engine, background mode)
                     │
                     ▼
              output/movie_20240101_120000.mp4  ← your movie
```

---

## Requirements

| Requirement | Notes |
|---|---|
| **Python 3.10+** | |
| **Blender 3.5 or newer** | [blender.org](https://www.blender.org/download/) |
| **OpenAI API key** | Entered at runtime, never stored |

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Running

```bash
cd movie_generator
python main.py
```

The program will ask for your OpenAI API key **once at startup** (it's never saved to disk).

### Example prompts

```
a 15-second animated short of a red ball bouncing across a checkerboard floor

a 30-second sunrise over mountains in a low-poly art style

a 20-second sci-fi scene with a rotating space station and stars

a 10-second cartoon of a yellow car driving down a colorful road
```

### Built-in commands

| Command | Action |
|---|---|
| `help` | Show command list |
| `new` | Reset conversation, start a new movie |
| `last` | Print path of the last generated movie |
| `blender` | Print the detected Blender path |
| `quit` | Exit |

---

## How it works

1. **API key prompt** — entered once, kept only in memory for the session.
2. **ChatGPT (GPT-4o)** receives your description plus a strict system prompt that forces it to produce a complete, self-contained `bpy` Python script.
3. The script is saved to `scripts/` and executed with:
   ```
   blender --background --python script.py
   ```
4. Blender uses the **Eevee** renderer (real-time, GPU-accelerated) instead of slow path-traced Cycles — frames render in seconds rather than minutes.
5. The finished MP4 is written to `output/` and the path is shown in the terminal.
6. If Blender reports an error, the error log is automatically sent back to ChatGPT for a one-shot auto-fix attempt.

---

## Troubleshooting

**Blender not found** — if it's not in your PATH, the program will ask you to type the full path manually. You can also set the `BLENDER_PATH` env variable:

```bash
BLENDER_PATH=/path/to/blender python main.py
```

**Render takes a long time** — Eevee is fast, but complex scenes or long animations still take time. Keep your first tests short (5–15 seconds).

**Script errors** — the program auto-retries once. If it still fails, the generated scripts are saved in `scripts/` — you can open them in Blender's Text Editor and debug manually.

---

## Project layout

```
movie_generator/
├── main.py           Entry point — chat loop and UI
├── gpt_client.py     OpenAI API wrapper (script generation + auto-fix)
├── blender_runner.py Blender detection, script execution, output handling
├── requirements.txt  Python dependencies (openai, rich)
├── output/           Generated MP4 files  (git-ignored)
└── scripts/          Generated .py scripts (git-ignored)
```
