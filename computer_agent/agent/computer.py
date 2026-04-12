"""PyAutoGUI wrapper that executes every computer action the AI can request.

Safety:
  - FAILSAFE is enabled: move mouse to the top-left corner of the screen to
    immediately abort all further actions.
  - A short sleep after each action lets the UI settle before the next frame
    is captured.
"""

import time

import pyautogui

# Moving the mouse to (0, 0) raises pyautogui.FailSafeException and stops everything.
pyautogui.FAILSAFE = True
# Small built-in pause between pyautogui calls.
pyautogui.PAUSE = 0.05

# How long to wait after an action before the next screenshot is taken.
_SETTLE_DELAY = 0.3


class ComputerController:
    def execute(self, fn_name: str, args: dict) -> str:
        """Dispatch a tool call to the appropriate pyautogui function.

        Returns "ok" on success or an error string on failure.
        """
        try:
            match fn_name:
                case "mouse_move":
                    pyautogui.moveTo(args["x"], args["y"], duration=0.2)

                case "left_click":
                    pyautogui.click(args["x"], args["y"])

                case "right_click":
                    pyautogui.rightClick(args["x"], args["y"])

                case "double_click":
                    pyautogui.doubleClick(args["x"], args["y"])

                case "type_text":
                    pyautogui.write(str(args["text"]), interval=0.04)

                case "press_key":
                    raw = str(args["key"])
                    # Support both "ctrl+c" and "ctrl c" separators.
                    keys = raw.replace("+", " ").split()
                    pyautogui.hotkey(*keys)

                case "scroll":
                    direction = args.get("direction", "down")
                    amount = int(args.get("amount", 3))
                    clicks = amount if direction == "down" else -amount
                    pyautogui.scroll(clicks, x=args["x"], y=args["y"])

                case "drag":
                    pyautogui.moveTo(args["start_x"], args["start_y"])
                    pyautogui.dragTo(
                        args["end_x"],
                        args["end_y"],
                        duration=0.4,
                        button="left",
                    )

                case _:
                    return f"unknown action: {fn_name}"

            time.sleep(_SETTLE_DELAY)
            return "ok"

        except pyautogui.FailSafeException:
            raise  # re-raise so the agent loop can catch and stop cleanly
        except Exception as exc:
            return f"error: {exc}"
