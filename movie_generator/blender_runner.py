"""
Blender runner — finds the Blender executable, saves generated scripts,
executes them in background mode, and reports results.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple


# Common Blender install locations across platforms
_BLENDER_CANDIDATES = [
    "blender",  # Already in $PATH
    "/usr/bin/blender",
    "/usr/local/bin/blender",
    "/snap/bin/blender",
    "/opt/blender/blender",
    # macOS
    "/Applications/Blender.app/Contents/MacOS/blender",
    # Windows (common versions)
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
]


class BlenderRunner:
    """Manages Blender script execution and output file handling."""

    def __init__(self, blender_path: str | None = None):
        # Priority: explicit arg → env var → auto-detect
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_output_path(self) -> Path:
        """Return a unique timestamped output MP4 path."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (self._output_dir / f"movie_{stamp}.mp4").resolve()

    def save_script(self, code: str, tag: str = "") -> Path:
        """Write *code* to a .py file and return its path."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"script_{stamp}{tag}.py"
        path = (self._scripts_dir / name).resolve()
        path.write_text(code, encoding="utf-8")
        return path

    def run_script(
        self, script_path: Path, output_path: Path, timeout: int = 7200
    ) -> Tuple[bool, str]:
        """
        Run *script_path* inside Blender (background mode).

        Returns:
            (True, "")              – success, output file exists
            (False, error_snippet)  – failure with captured error text
        """
        cmd = [
            self.blender_path,
            "--background",
            "--python", str(script_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, f"Blender timed out after {timeout // 60} minutes."
        except FileNotFoundError:
            return False, f"Blender executable not found: {self.blender_path}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

        # Success: Blender exited 0 AND the output file was written
        if result.returncode == 0 and output_path.exists():
            return True, ""

        # Collect the most relevant error lines from stdout + stderr
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        error_lines = _filter_error_lines(combined)
        snippet = "\n".join(error_lines[-40:]) if error_lines else combined[-3000:]
        return False, snippet

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _auto_find() -> str:
        for candidate in _BLENDER_CANDIDATES:
            if shutil.which(candidate):
                return candidate
            if os.path.isfile(candidate):
                return candidate

        # Fall back to asking the user
        print("\nBlender was not found automatically.")
        while True:
            path = input("Enter the full path to your Blender executable: ").strip()
            if path and os.path.isfile(path):
                return path
            if path and shutil.which(path):
                return path
            print(f"  Not found: {path!r}  — please try again.")


def _filter_error_lines(text: str) -> list[str]:
    """Return lines that look like errors or tracebacks."""
    keywords = ("error", "traceback", "exception", "syntaxerror",
                 "nameerror", "attributeerror", "typeerror", "line ")
    return [
        ln for ln in text.splitlines()
        if any(kw in ln.lower() for kw in keywords)
    ]
