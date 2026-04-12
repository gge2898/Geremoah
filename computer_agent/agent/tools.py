"""OpenAI-format tool definitions for Gemma 3 via Ollama.

Each entry is a function the AI can call to control the computer.
The special 'task_complete' function signals the agent loop to stop.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mouse_move",
            "description": "Move the mouse cursor to the given pixel coordinates on screen without clicking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X pixel coordinate"},
                    "y": {"type": "integer", "description": "Y pixel coordinate"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "left_click",
            "description": "Click the left mouse button at the given pixel coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X pixel coordinate"},
                    "y": {"type": "integer", "description": "Y pixel coordinate"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "right_click",
            "description": "Click the right mouse button at the given pixel coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X pixel coordinate"},
                    "y": {"type": "integer", "description": "Y pixel coordinate"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_click",
            "description": "Double-click the left mouse button at the given pixel coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X pixel coordinate"},
                    "y": {"type": "integer", "description": "Y pixel coordinate"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type the given text string using the keyboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to type"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": (
                "Press a keyboard key or key combination. "
                "Use '+' to combine keys, e.g. 'ctrl+c', 'alt+f4', 'ctrl+shift+t'. "
                "Single key examples: 'Return', 'Escape', 'Tab', 'BackSpace', 'Delete', "
                "'Up', 'Down', 'Left', 'Right', 'F1'...'F12', 'space'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key or key combo to press"},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the mouse wheel at the given coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X pixel coordinate"},
                    "y": {"type": "integer", "description": "Y pixel coordinate"},
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "description": "Scroll direction",
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Number of scroll clicks (default 3)",
                    },
                },
                "required": ["x", "y", "direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drag",
            "description": "Click and drag the mouse from one coordinate to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Start X coordinate"},
                    "start_y": {"type": "integer", "description": "Start Y coordinate"},
                    "end_x": {"type": "integer", "description": "End X coordinate"},
                    "end_y": {"type": "integer", "description": "End Y coordinate"},
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": (
                "Call this function when the task has been fully completed. "
                "Provide a short summary of what was accomplished."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Summary of what was accomplished",
                    },
                },
                "required": ["message"],
            },
        },
    },
]
