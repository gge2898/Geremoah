#!/usr/bin/env python3
"""
AI Movie Generator  —  single-file edition
==========================================
Describe any movie in plain English → ChatGPT writes the Blender Python code
→ Blender renders it with the fast Eevee engine → MP4 saved to output/

Requirements
------------
  • Python 3.10+  OR  use the pre-built executable (no Python needed)
  • Blender 3.5+  →  https://www.blender.org/download/
  • OpenAI API key  (entered at startup, never stored to disk)

Usage
-----
  python movie_generator.py
"""

# ── Auto-install Python dependencies (one-time) ───────────────────────────────
import subprocess
import sys


def _bootstrap() -> None:
    needed = []
    for pkg in ("openai", "rich"):
        try:
            __import__(pkg)
        except ImportError:
            needed.append(pkg)
    if needed:
        print(f"One-time setup: installing {', '.join(needed)} …")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *needed],
            stdout=subprocess.DEVNULL,
        )
        print("Done!\n")


_bootstrap()

# ── Standard imports ──────────────────────────────────────────────────────────
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import openai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

# =============================================================================
#  GPT CLIENT
# =============================================================================

_SYSTEM_PROMPT = """\
You are an expert Blender 3D animation Python developer.
When the user describes a movie they want, you must:

1. Reply with ONE short sentence describing what you will create (no code here).
2. Then output a COMPLETE, self-contained Blender Python script inside a
   ```python ... ``` code block.

━━━━━━━━━━━  MANDATORY SCRIPT REQUIREMENTS  ━━━━━━━━━━━
• import bpy  (always first line inside the code block)
• Clear the default scene:
      bpy.ops.wm.read_factory_settings(use_empty=True)
• Set render engine to BLENDER_EEVEE  (fast real-time renderer)
• Set output path EXACTLY to: {output_path}
• Set file format:
      scene = bpy.context.scene
      scene.render.image_settings.file_format = 'FFMPEG'
      scene.render.ffmpeg.format = 'MPEG4'
      scene.render.ffmpeg.codec = 'H264'
      scene.render.ffmpeg.constant_rate_factor = 'HIGH'
• Frame rate: 24 fps  (scene.render.fps = 24)
• Resolution: 1280 × 720  (unless the user asks for something else)
• Set frame_start and frame_end to match the requested length
  (e.g. 10 s → frames 1–240 at 24 fps)
• Create ALL scene content programmatically using bpy:
    – At least one camera set as scene.camera
    – At least one light (Sun, Point, or Area)
    – All 3-D objects, materials, textures, and keyframe animations
• Materials MUST use nodes  (mat.use_nodes = True)
• NO external file imports — everything built from scratch with bpy
• Very last line of the script MUST be:
      bpy.ops.render.render(animation=True)

Write ONLY valid Python / bpy code inside the code block.
Do NOT add explanations inside the code block.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class _GPTClient:
    """Wraps the OpenAI Chat Completions API for movie-script generation."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._history: list[dict] = []

    def generate_blender_script(
        self, user_request: str, output_path: str
    ) -> Tuple[Optional[str], str]:
        system = _SYSTEM_PROMPT.replace("{output_path}", output_path)
        user_msg = (
            f"Create a movie for me:\n\n{user_request}\n\n"
            f"Output file path (use exactly): {output_path}"
        )
        self._history.append({"role": "user", "content": user_msg})
        reply = self._chat(system)
        return self._extract_code(reply), self._extract_description(reply)

    def fix_script(
        self, broken_script: str, error_text: str, output_path: str
    ) -> Tuple[Optional[str], str]:
        system = _SYSTEM_PROMPT.replace("{output_path}", output_path)
        fix_msg = (
            "The Blender script failed with this error:\n\n"
            f"```\n{error_text[:3000]}\n```\n\n"
            "Here is the original script:\n\n"
            f"```python\n{broken_script}\n```\n\n"
            f"Output path (keep it unchanged): {output_path}\n\n"
            "Please provide a completely corrected, working script."
        )
        self._history.append({"role": "user", "content": fix_msg})
        reply = self._chat(system)
        return self._extract_code(reply), reply

    def reset(self) -> None:
        self._history.clear()

    def _chat(self, system_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                *self._history,
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        reply = response.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": reply})
        return reply

    @staticmethod
    def _extract_code(text: str) -> Optional[str]:
        for pattern in (r"```python\s*(.*?)\s*```", r"```\s*(.*?)\s*```"):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                code = m.group(1).strip()
                if "import bpy" in code:
                    return code
        return None

    @staticmethod
    def _extract_description(text: str) -> str:
        clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
        lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
        return lines[0] if lines else "Generating your movie…"


# =============================================================================
#  BLENDER RUNNER
# =============================================================================

_BLENDER_CANDIDATES = [
    "blender",
    "/usr/bin/blender",
    "/usr/local/bin/blender",
    "/snap/bin/blender",
    "/opt/blender/blender",
    # macOS
    "/Applications/Blender.app/Contents/MacOS/blender",
    # Windows (common versions — newest first)
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
]


class _BlenderRunner:
    def __init__(self, blender_path: Optional[str] = None):
        if blender_path:
            self.blender_path = blender_path
        elif os.environ.get("BLENDER_PATH"):
            self.blender_path = os.environ["BLENDER_PATH"]
        else:
            self.blender_path = self._auto_find()

        self._output_dir = Path("output")
        self._scripts_dir = Path("scripts")
        self._output_dir.mkdir(exist_ok=True)
        self._scripts_dir.mkdir(exist_ok=True)

    def get_output_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (self._output_dir / f"movie_{stamp}.mp4").resolve()

    def save_script(self, code: str, tag: str = "") -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = (self._scripts_dir / f"script_{stamp}{tag}.py").resolve()
        path.write_text(code, encoding="utf-8")
        return path

    def run_script(
        self, script_path: Path, output_path: Path, timeout: int = 7200
    ) -> Tuple[bool, str]:
        cmd = [self.blender_path, "--background", "--python", str(script_path)]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return False, f"Blender timed out after {timeout // 60} minutes."
        except FileNotFoundError:
            return False, f"Blender executable not found: {self.blender_path}"
        except Exception as exc:
            return False, str(exc)

        if result.returncode == 0 and output_path.exists():
            return True, ""

        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        error_lines = [
            ln for ln in combined.splitlines()
            if any(
                kw in ln.lower()
                for kw in ("error", "traceback", "exception", "line ")
            )
        ]
        snippet = "\n".join(error_lines[-40:]) if error_lines else combined[-3000:]
        return False, snippet

    @staticmethod
    def _auto_find() -> str:
        for candidate in _BLENDER_CANDIDATES:
            if shutil.which(candidate):
                return candidate
            if os.path.isfile(candidate):
                return candidate
        print("\nBlender was not found automatically.")
        while True:
            path = input("Enter the full path to your Blender executable: ").strip()
            if path and (os.path.isfile(path) or shutil.which(path)):
                return path
            print(f"  Not found: {path!r}  — please try again.")


# =============================================================================
#  TERMINAL UI  &  MAIN LOOP
# =============================================================================

console = Console()

_BANNER = """\
[bold cyan]  ╔═══════════════════════════════════════╗
  ║      AI  MOVIE  GENERATOR             ║
  ║  ChatGPT  +  Blender  Eevee Engine   ║
  ╚═══════════════════════════════════════╝[/bold cyan]

[dim]• Describe any movie in plain English
• ChatGPT writes the Blender Python code
• Blender renders it with the fast Eevee engine
• Your MP4 is saved to the  output/  folder[/dim]
"""

_HELP = """\
[bold]Commands:[/bold]
  [cyan]new[/cyan]       — start a new movie (resets conversation)
  [cyan]last[/cyan]      — show path of the last generated movie
  [cyan]blender[/cyan]   — print the detected Blender path
  [cyan]help[/cyan]      — show this message
  [cyan]quit[/cyan]      — exit
"""


def _ask_api_key() -> str:
    console.print(_BANNER)
    console.print(Panel.fit(
        "[bold yellow]Before we start, enter your OpenAI API key.[/bold yellow]\n"
        "[dim]It's only used this session and is never saved to disk.[/dim]",
        border_style="yellow",
    ))
    while True:
        key = Prompt.ask("[bold]OpenAI API key[/bold]", password=True).strip()
        if key.startswith("sk-") and len(key) > 20:
            return key
        console.print("[red]That doesn't look like a valid key (should start with 'sk-').[/red]")


def _render_msg(output_path: Path) -> None:
    console.print(Panel.fit(
        f"[bold yellow]Rendering in Blender (Eevee)[/bold yellow]\n"
        f"[dim]Output → {output_path}[/dim]\n\n"
        "[dim]This can take a few minutes. Blender is rendering each frame…[/dim]",
        border_style="yellow",
    ))


def _success_msg(output_path: Path) -> None:
    console.print(Panel.fit(
        Text.assemble(("Movie ready!  ", "bold green"), (str(output_path), "green underline")),
        border_style="green",
        title="[bold green]Done[/bold green]",
    ))
    console.print()


def main() -> None:
    # Change to the script's directory so output/ and scripts/ are predictable
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    api_key = _ask_api_key()

    console.print("\n[green]Finding Blender…[/green]")
    try:
        runner = _BlenderRunner()
    except Exception as exc:
        console.print(f"[red]Could not initialise Blender: {exc}[/red]")
        sys.exit(1)

    console.print(f"[dim]Blender: {runner.blender_path}[/dim]")
    gpt = _GPTClient(api_key)
    last_output: Optional[str] = None

    console.print()
    console.print(Rule("[bold cyan]Ready[/bold cyan]"))
    console.print("[dim]Describe the movie you want — style, length, story, anything.[/dim]")
    console.print("[dim]Type [bold]help[/bold] for commands.[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if not user_input:
            continue

        low = user_input.lower()

        if low in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break
        if low == "help":
            console.print(_HELP)
            continue
        if low == "new":
            gpt.reset()
            console.print("[green]Conversation reset — ready for a new movie.[/green]")
            continue
        if low == "last":
            console.print(f"[green]{last_output}[/green]" if last_output
                          else "[yellow]No movie generated yet.[/yellow]")
            continue
        if low == "blender":
            console.print(f"[dim]{runner.blender_path}[/dim]")
            continue

        # ── Generate script ────────────────────────────────────────────────
        output_path = runner.get_output_path()

        with console.status("[bold green]ChatGPT is writing your Blender script…[/bold green]"):
            try:
                script, description = gpt.generate_blender_script(user_input, str(output_path))
            except Exception as exc:
                console.print(f"[red]OpenAI API error: {exc}[/red]")
                continue

        if not script:
            console.print(
                "[red]ChatGPT didn't return a valid Blender script. "
                "Try rephrasing your request.[/red]"
            )
            continue

        console.print(f"\n[cyan]ChatGPT:[/cyan] {description}\n")
        script_path = runner.save_script(script)
        console.print(f"[dim]Script → {script_path}[/dim]")

        # ── First render attempt ───────────────────────────────────────────
        _render_msg(output_path)
        success, error = runner.run_script(script_path, output_path)

        if success:
            last_output = str(output_path)
            _success_msg(output_path)
            continue

        # ── Auto-fix on failure ────────────────────────────────────────────
        console.print(f"\n[red]Blender error:[/red]\n[dim]{error[:1500]}[/dim]\n")
        console.print("[yellow]Asking ChatGPT to fix the script…[/yellow]")

        with console.status("[bold yellow]Fixing…[/bold yellow]"):
            try:
                fixed_script, _ = gpt.fix_script(script, error, str(output_path))
            except Exception as exc:
                console.print(f"[red]OpenAI API error during fix: {exc}[/red]")
                continue

        if not fixed_script:
            console.print("[red]Could not generate a fix. Try rephrasing your movie idea.[/red]")
            continue

        fixed_path = runner.save_script(fixed_script, tag="_fixed")
        console.print(f"[dim]Fixed script → {fixed_path}[/dim]")

        _render_msg(output_path)
        success2, error2 = runner.run_script(fixed_path, output_path)

        if success2:
            last_output = str(output_path)
            _success_msg(output_path)
        else:
            console.print(
                f"\n[red]Still failed after auto-fix.[/red]\n[dim]{error2[:1000]}[/dim]\n"
                "[yellow]Tip: check the scripts/ folder for the generated .py files.[/yellow]\n"
            )


if __name__ == "__main__":
    main()
