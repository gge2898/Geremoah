#!/usr/bin/env python3
"""AI Computer Control Agent — entry point.

This executable is self-contained: on first launch it automatically
downloads and installs Ollama, pulls the Gemma 3 model, and starts the
Bluetooth server. No manual installation is required on the computer.

Usage:
  ./AIControlAgent          (Linux / macOS)
  AIControlAgent.exe        (Windows)

Environment variables (optional):
  OLLAMA_MODEL    Override model, default: gemma3:4b
                  Use gemma3:12b for smarter (but slower) results.
"""

import os
import sys


def _banner() -> None:
    model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    print()
    print("=" * 60)
    print("  AI Computer Control Agent")
    print(f"  Model : {model}")
    print("  Safety: Move mouse to top-left corner to stop AI")
    print("=" * 60)
    print()


def main() -> None:
    _banner()

    # ── Step 1: Auto-setup (Ollama + model) ──────────────────────────────
    print("[1/3] Checking setup...")
    try:
        from setup_manager import ensure_ready
        ensure_ready()
    except Exception as exc:
        print(f"\nSetup failed: {exc}")
        print("Please report this at: https://github.com/gge2898/Geremoah/issues")
        input("Press Enter to exit.")
        sys.exit(1)

    # ── Step 2: Start Bluetooth server ───────────────────────────────────
    print("\n[2/3] Starting Bluetooth server...")
    try:
        import bluetooth  # noqa: F401  (verify PyBluez2 is available)
    except ImportError:
        print(
            "\nERROR: Bluetooth library not available.\n"
            "On Linux, install: sudo apt install libbluetooth-dev\n"
            "Then reinstall this agent."
        )
        input("Press Enter to exit.")
        sys.exit(1)

    print("[3/3] Ready. Waiting for Android app to connect...\n")
    print("      Tip: Make sure your phone is paired with this computer")
    print("      via Bluetooth before connecting from the app.\n")

    from server import run_server
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
