#!/usr/bin/env python3
"""
AI Movie Generator
==================
Describe any movie in plain English → ChatGPT writes a Blender Python script
→ Blender renders it using the real-time Eevee engine → MP4 saved to output/

Usage:
    python main.py
"""

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

console = Console()

# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------
_BANNER = """\
[bold cyan]  ╔═══════════════════════════════════════╗
  ║      AI  MOVIE  GENERATOR             ║
  ║  ChatGPT  +  Blender  Eevee engine   ║
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
  [cyan]blender[/cyan]   — print the detected Blender executable path
  [cyan]help[/cyan]      — show this message
  [cyan]quit[/cyan]      — exit
"""


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def ask_api_key() -> str:
    console.print(_BANNER)
    console.print(Panel.fit(
        "[bold yellow]Before we start, enter your OpenAI API key.[/bold yellow]\n"
        "[dim]It will only be used in this session and never stored to disk.[/dim]",
        border_style="yellow",
    ))
    while True:
        key = Prompt.ask("[bold]OpenAI API key[/bold]", password=True)
        key = key.strip()
        if key.startswith("sk-") and len(key) > 20:
            return key
        console.print("[red]That doesn't look like a valid API key (should start with 'sk-').[/red]")


def main() -> None:
    api_key = ask_api_key()

    # Lazy imports — after we have the key
    from gpt_client import GPTClient
    from blender_runner import BlenderRunner

    console.print("\n[green]Finding Blender...[/green]")
    try:
        runner = BlenderRunner()
    except Exception as exc:
        console.print(f"[red]Could not initialise Blender runner: {exc}[/red]")
        sys.exit(1)

    console.print(f"[dim]Blender: {runner.blender_path}[/dim]")

    gpt = GPTClient(api_key)
    last_output: str | None = None

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

        # ── Built-in commands ─────────────────────────────────────────────
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
            if last_output:
                console.print(f"[green]Last movie: {last_output}[/green]")
            else:
                console.print("[yellow]No movie has been generated yet.[/yellow]")
            continue

        if low == "blender":
            console.print(f"[dim]{runner.blender_path}[/dim]")
            continue

        # ── Generate script ───────────────────────────────────────────────
        output_path = runner.get_output_path()

        with console.status("[bold green]ChatGPT is writing your Blender script…[/bold green]"):
            try:
                script, description = gpt.generate_blender_script(user_input, str(output_path))
            except Exception as exc:
                console.print(f"[red]OpenAI API error: {exc}[/red]")
                continue

        if not script:
            console.print(
                "[red]ChatGPT did not return a valid Blender script. "
                "Try rephrasing your request.[/red]"
            )
            continue

        console.print(f"\n[cyan]ChatGPT:[/cyan] {description}\n")

        script_path = runner.save_script(script)
        console.print(f"[dim]Script → {script_path}[/dim]")

        # ── Run Blender ───────────────────────────────────────────────────
        _render_progress(output_path)

        success, error = runner.run_script(script_path, output_path)

        if success:
            last_output = str(output_path)
            _show_success(output_path)
            continue

        # ── Auto-fix on first failure ─────────────────────────────────────
        console.print(f"\n[red]Blender error:[/red]\n[dim]{error[:1500]}[/dim]\n")
        console.print("[yellow]Asking ChatGPT to fix the script…[/yellow]")

        with console.status("[bold yellow]Fixing…[/bold yellow]"):
            try:
                fixed_script, _ = gpt.fix_script(script, error, str(output_path))
            except Exception as exc:
                console.print(f"[red]OpenAI API error during fix: {exc}[/red]")
                continue

        if not fixed_script:
            console.print("[red]Could not generate a fix. Try describing your movie differently.[/red]")
            continue

        fixed_path = runner.save_script(fixed_script, tag="_fixed")
        console.print(f"[dim]Fixed script → {fixed_path}[/dim]")

        _render_progress(output_path)
        success2, error2 = runner.run_script(fixed_path, output_path)

        if success2:
            last_output = str(output_path)
            _show_success(output_path)
        else:
            console.print(
                f"\n[red]Still failed after auto-fix.[/red]\n"
                f"[dim]{error2[:1000]}[/dim]\n"
                "[yellow]Tip: check the saved script files in scripts/ for details.[/yellow]\n"
            )


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _render_progress(output_path) -> None:
    console.print(
        Panel.fit(
            f"[bold yellow]Rendering in Blender (Eevee)[/bold yellow]\n"
            f"[dim]Output → {output_path}[/dim]\n\n"
            "[dim]This can take a few minutes. Blender is rendering each frame…[/dim]",
            border_style="yellow",
        )
    )


def _show_success(output_path) -> None:
    console.print(
        Panel.fit(
            Text.assemble(
                ("Movie ready! ", "bold green"),
                (str(output_path), "green underline"),
            ),
            border_style="green",
            title="[bold green]Done[/bold green]",
        )
    )
    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Make sure script/ and output/ relative paths resolve from the script's
    # directory, not wherever the user ran the command from.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
