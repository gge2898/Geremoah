"""Automatic first-run setup: installs Ollama and pulls the Gemma model.

This module is called by main.py before starting the Bluetooth server.
It uses only Python stdlib (urllib, subprocess, os, platform) so that
PyInstaller can bundle it into a self-contained executable with no external
download tools required.
"""

import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_BASE_URL = "http://localhost:11434"


# ── Ollama download URLs ────────────────────────────────────────────────────

_LINUX_INSTALL_SCRIPT = "https://ollama.com/install.sh"
_WINDOWS_INSTALLER    = "https://ollama.com/download/OllamaSetup.exe"
_MACOS_ZIP            = "https://ollama.com/download/Ollama-darwin.zip"


def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 // total_size)
        mb = downloaded / 1_048_576
        total_mb = total_size / 1_048_576
        print(f"\r  Downloading... {pct}%  ({mb:.0f} / {total_mb:.0f} MB)   ", end="", flush=True)


def _download(url: str, dest: str) -> None:
    print(f"  Fetching {url}")
    urllib.request.urlretrieve(url, dest, reporthook=_progress_hook)
    print()  # newline after progress bar


# ── Ollama installation ─────────────────────────────────────────────────────

def _ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def _install_ollama_linux() -> None:
    script = "/tmp/_ollama_install.sh"
    _download(_LINUX_INSTALL_SCRIPT, script)
    os.chmod(script, 0o755)
    result = subprocess.run(["sh", script], capture_output=False)
    if result.returncode != 0:
        raise RuntimeError("Ollama install script failed.")


def _install_ollama_windows() -> None:
    installer = str(Path(os.environ.get("TEMP", ".")) / "OllamaSetup.exe")
    _download(_WINDOWS_INSTALLER, installer)
    # /S = silent install
    result = subprocess.run([installer, "/S"])
    if result.returncode != 0:
        raise RuntimeError("Ollama installer exited with non-zero code.")
    # Add Ollama to PATH for this process
    ollama_bin = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    os.environ["PATH"] = str(ollama_bin) + os.pathsep + os.environ.get("PATH", "")


def _install_ollama_macos() -> None:
    zip_path = "/tmp/Ollama.zip"
    _download(_MACOS_ZIP, zip_path)
    subprocess.run(["unzip", "-q", "-o", zip_path, "-d", "/Applications"], check=True)
    os.remove(zip_path)
    # Symlink the CLI so it's on PATH
    cli = "/Applications/Ollama.app/Contents/Resources/ollama"
    link = "/usr/local/bin/ollama"
    if os.path.exists(cli) and not os.path.exists(link):
        os.makedirs("/usr/local/bin", exist_ok=True)
        os.symlink(cli, link)


def install_ollama() -> None:
    system = platform.system()
    print(f"Installing Ollama on {system}...")
    if system == "Linux":
        _install_ollama_linux()
    elif system == "Windows":
        _install_ollama_windows()
    elif system == "Darwin":
        _install_ollama_macos()
    else:
        raise RuntimeError(f"Unsupported OS: {system}. Please install Ollama manually: https://ollama.com")
    print("Ollama installed.")


# ── Ollama process management ───────────────────────────────────────────────

def _ollama_running() -> bool:
    try:
        import urllib.request as req
        req.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def start_ollama() -> None:
    if _ollama_running():
        return
    print("Starting Ollama service...")
    kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    subprocess.Popen(["ollama", "serve"], **kwargs)
    # Wait up to 15 seconds for Ollama to become ready
    for _ in range(30):
        time.sleep(0.5)
        if _ollama_running():
            print("Ollama is ready.")
            return
    raise RuntimeError(
        "Ollama did not start in time. Try running 'ollama serve' manually in a terminal."
    )


# ── Model management ────────────────────────────────────────────────────────

def _model_available(model: str) -> bool:
    try:
        import json
        import urllib.request as req
        with req.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
        names = [m["name"] for m in data.get("models", [])]
        # Match "gemma3:4b" against "gemma3:4b" or "gemma3" against "gemma3:latest"
        return any(n == model or n.startswith(model + ":") for n in names)
    except Exception:
        return False


def pull_model(model: str) -> None:
    if _model_available(model):
        print(f"Model '{model}' is already available.")
        return
    print(f"Pulling model '{model}' — this may take a few minutes on first run...")
    print("(The model is downloaded once and cached locally.)")
    result = subprocess.run(["ollama", "pull", model])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to pull model '{model}'.")
    print(f"Model '{model}' ready.")


# ── Bluetooth / discoverable setup ─────────────────────────────────────────

def setup_bluetooth() -> None:
    if platform.system() != "Linux":
        return  # bluetoothctl is Linux-specific; skip on Windows/macOS
    try:
        subprocess.run(
            ["bluetoothctl", "discoverable", "on"],
            capture_output=True,
            timeout=5,
        )
        subprocess.run(
            ["bluetoothctl", "pairable", "on"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass  # non-critical — user may have already paired


# ── Main entry point ────────────────────────────────────────────────────────

def ensure_ready() -> None:
    """Install Ollama, pull the model, and start the service if needed.

    This is called once at startup. Safe to call if everything is already set up.
    """
    if not _ollama_installed():
        install_ollama()

    start_ollama()
    pull_model(MODEL)
    setup_bluetooth()
