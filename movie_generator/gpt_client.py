"""
ChatGPT client — generates Blender Python scripts from natural-language movie descriptions.
"""

import re
from typing import Optional, Tuple

import openai

# ---------------------------------------------------------------------------
# System prompt sent to GPT on every request
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are an expert Blender 3D animation Python developer.
When the user describes a movie they want, you must:

1. Reply with ONE short sentence describing what you will create (no code here).
2. Then output a COMPLETE, self-contained Blender Python script inside a
   ```python ... ``` code block.

━━━━━━━━━━━  MANDATORY SCRIPT REQUIREMENTS  ━━━━━━━━━━━
• import bpy  (always first line)
• Clear the default scene:
      bpy.ops.wm.read_factory_settings(use_empty=True)
• Set render engine to BLENDER_EEVEE  (fast real-time renderer)
• Set output path EXACTLY to: {output_path}
• Set file format:
      scene.render.image_settings.file_format = 'FFMPEG'
      scene.render.ffmpeg.format = 'MPEG4'
      scene.render.ffmpeg.codec = 'H264'
      scene.render.ffmpeg.constant_rate_factor = 'HIGH'
• Frame rate: 24 fps
• Resolution: 1280 × 720  (unless the user asks for something else)
• Set frame_start and frame_end to match the requested length
  (e.g. 10 s → frames 1–240)
• Create ALL scene content programmatically:
    – At least one camera (set as scene.camera)
    – At least one light (Sun, Point, or Area)
    – All 3-D objects, materials, textures, and keyframe animations
• Materials MUST use nodes  (mat.use_nodes = True)
• NO external file imports — everything built from scratch with bpy
• Very last line of the script:
      bpy.ops.render.render(animation=True)

Write ONLY valid Python / bpy code inside the code block.
Do NOT add explanations inside the code block.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class GPTClient:
    """Wraps the OpenAI Chat Completions API for movie-script generation."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        # Keep full conversation so GPT remembers earlier context
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_blender_script(
        self, user_request: str, output_path: str
    ) -> Tuple[Optional[str], str]:
        """
        Ask GPT to create a Blender script for *user_request*.
        Returns (script_code, description_text).
        """
        system = _SYSTEM_PROMPT.replace("{output_path}", output_path)

        user_msg = (
            f"Create a movie for me:\n\n{user_request}\n\n"
            f"Output file path: {output_path}"
        )
        self._history.append({"role": "user", "content": user_msg})

        reply = self._chat(system)

        script = self._extract_code(reply)
        description = self._extract_description(reply)
        return script, description

    def fix_script(
        self, broken_script: str, error_text: str, output_path: str
    ) -> Tuple[Optional[str], str]:
        """
        Ask GPT to fix a broken Blender script based on the error message.
        Returns (fixed_script_code, reply_text).
        """
        system = _SYSTEM_PROMPT.replace("{output_path}", output_path)

        fix_msg = (
            "The Blender script failed with this error:\n\n"
            f"```\n{error_text[:3000]}\n```\n\n"
            "Here is the original script:\n\n"
            f"```python\n{broken_script}\n```\n\n"
            f"Output path (keep it unchanged): {output_path}\n\n"
            "Please provide a completely corrected script."
        )
        self._history.append({"role": "user", "content": fix_msg})

        reply = self._chat(system)
        script = self._extract_code(reply)
        return script, reply

    def reset(self):
        """Clear conversation history (start fresh)."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
        # Prefer ```python ... ``` blocks
        for pattern in (r"```python\s*(.*?)\s*```", r"```\s*(.*?)\s*```"):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                code = m.group(1).strip()
                if "import bpy" in code:
                    return code
        return None

    @staticmethod
    def _extract_description(text: str) -> str:
        # Strip code blocks and return the first non-empty line
        clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
        lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
        return lines[0] if lines else "Generating your movie..."
