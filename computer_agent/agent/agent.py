"""Gemma 3 agent loop via Ollama.

The agent receives a task, watches the screen video feed, and uses
function-calling to control the computer until the task is complete
or the iteration limit is reached.

Status updates are delivered through an optional callback so that the
Bluetooth server can stream them back to the Android app.
"""

import base64
import json
from typing import Callable

import ollama
import pyautogui

from .computer import ComputerController
from .display import Display
from .screen import FrameBuffer
from .tools import TOOLS

MODEL = "gemma3:4b"  # override with OLLAMA_MODEL env var or at construction
MAX_ITERS = 50

SYSTEM_PROMPT = """You are an AI computer control agent. You can see the user's screen through
a live video feed. A fresh screenshot is provided before each of your responses.

Use the available tools to control the mouse and keyboard and complete the user's task.
Think step by step. After each action, you will automatically receive an updated screenshot.

Important rules:
- Always describe what you see on the screen before deciding what to do.
- Use left_click to click buttons, links, and UI elements.
- Use type_text to enter text into focused input fields.
- Use press_key for keyboard shortcuts (e.g. "Return", "ctrl+c", "Escape").
- When the task is fully complete, call task_complete with a short summary.
- If you are stuck after several attempts, call task_complete explaining what happened."""

StatusCallback = Callable[[dict], None]


def _noop_callback(msg: dict) -> None:
    pass


class AgentLoop:
    def __init__(
        self,
        model: str = MODEL,
        status_callback: StatusCallback = _noop_callback,
    ):
        self._model = model
        self._callback = status_callback
        self._buffer = FrameBuffer(fps=5, buffer_seconds=3)
        self._controller = ComputerController()
        self._display = Display()

    def _send_status(self, msg: dict) -> None:
        """Send a status update both to the terminal and over Bluetooth."""
        self._callback(msg)
        # Mirror to terminal as well
        match msg.get("type"):
            case "thinking":
                self._display.gemma_text(msg.get("message", ""))
            case "action":
                self._display.action(
                    msg.get("action", "?"),
                    {k: v for k, v in msg.items() if k not in ("type", "action")},
                )
            case "done":
                self._display.task_done(msg.get("message", ""))
            case "error":
                self._display.error(msg.get("message", ""))

    def _frame_b64(self) -> str:
        return base64.b64encode(self._buffer.latest_frame()).decode()

    def run(self, task: str) -> None:
        """Execute a task. Blocks until done or MAX_ITERS is reached."""
        self._buffer.start()
        self._display.task_start(task)

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        for iteration in range(1, MAX_ITERS + 1):
            self._display.iteration(iteration)

            # Attach the latest frame and the task / continuation prompt
            user_content = task if iteration == 1 else "Here is the current state of the screen."
            messages.append(
                {
                    "role": "user",
                    "content": user_content,
                    "images": [self._frame_b64()],
                }
            )

            try:
                response = ollama.chat(
                    model=self._model,
                    messages=messages,
                    tools=TOOLS,
                )
            except Exception as exc:
                self._send_status({"type": "error", "message": f"Ollama error: {exc}"})
                return

            msg = response["message"]
            messages.append(msg)

            # Print/stream text reasoning
            text = msg.get("content", "").strip()
            if text:
                self._send_status({"type": "thinking", "message": text})

            tool_calls = msg.get("tool_calls") or []

            # No tool calls → Gemma considers the task done
            if not tool_calls:
                self._send_status({"type": "done", "message": text or "Task complete."})
                return

            # Execute each tool call in order
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"].get("arguments", {})
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except json.JSONDecodeError:
                        fn_args = {}

                # Build status payload
                status_payload = {"type": "action", "action": fn_name, **fn_args}
                self._send_status(status_payload)

                # Sentinel: task is done
                if fn_name == "task_complete":
                    done_msg = fn_args.get("message", "Task complete.")
                    self._send_status({"type": "done", "message": done_msg})
                    return

                # Execute the action
                try:
                    result = self._controller.execute(fn_name, fn_args)
                except pyautogui.FailSafeException:
                    self._send_status(
                        {
                            "type": "error",
                            "message": "Failsafe triggered (mouse moved to corner). Stopping.",
                        }
                    )
                    return

                # Feed result back to model
                messages.append(
                    {
                        "role": "tool",
                        "content": result,
                    }
                )

        self._send_status(
            {
                "type": "error",
                "message": f"Reached the maximum of {MAX_ITERS} iterations without completing the task.",
            }
        )
