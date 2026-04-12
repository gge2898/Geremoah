#!/usr/bin/env python3
"""Entry point for the AI Computer Control agent.

Run this on the computer you want to control. It starts a Bluetooth
RFCOMM server that the Android app connects to.

Prerequisites:
  1. Install Ollama:  curl -fsSL https://ollama.com/install.sh | sh
  2. Pull the model:  ollama pull gemma3:4b   (or gemma3:12b)
  3. Start Ollama:    ollama serve
  4. Make the computer discoverable via Bluetooth
  5. Run this script: python main.py

Environment variables:
  OLLAMA_MODEL   Override the default model (default: gemma3:4b)
"""

import os
import sys


def check_ollama() -> bool:
    """Return True if Ollama is reachable."""
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False


def main() -> None:
    print("=" * 60)
    print("  AI Computer Control Agent")
    print(f"  Model : {os.environ.get('OLLAMA_MODEL', 'gemma3:4b')}")
    print("  Safety: Move mouse to top-left corner to abort at any time")
    print("=" * 60)
    print()

    if not check_ollama():
        print("ERROR: Cannot reach Ollama. Make sure it is installed and running:")
        print("  curl -fsSL https://ollama.com/install.sh | sh")
        print("  ollama pull gemma3:4b")
        print("  ollama serve")
        sys.exit(1)

    print("Ollama is running.")

    from server import run_server
    run_server()


if __name__ == "__main__":
    main()
