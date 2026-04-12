"""Continuous screen capture at a fixed FPS using a background daemon thread.

The FrameBuffer stores the last few seconds of frames. Call latest_frame()
to get the most recent PNG bytes to send to Gemma 3.
"""

import threading
import time
from collections import deque
from io import BytesIO

import mss
from PIL import Image

# Gemma 3 vision works well up to about 1280px on the longest side.
MAX_WIDTH = 1280
MAX_HEIGHT = 720


class FrameBuffer:
    def __init__(self, fps: int = 5, buffer_seconds: int = 3):
        self._fps = fps
        self._frames: deque[bytes] = deque(maxlen=fps * buffer_seconds)
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        """Start the background capture thread. Safe to call multiple times."""
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()

    def stop(self) -> None:
        self._running = False

    def _capture_loop(self) -> None:
        interval = 1.0 / self._fps
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary monitor
            while self._running:
                try:
                    raw = sct.grab(monitor)
                    img = Image.frombytes("RGB", raw.size, raw.rgb)
                    img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
                    buf = BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    frame_bytes = buf.getvalue()
                    with self._lock:
                        self._frames.append(frame_bytes)
                except Exception:
                    pass  # don't crash the capture thread on transient errors
                time.sleep(interval)

    def latest_frame(self) -> bytes:
        """Return the most recent captured frame as PNG bytes.

        Blocks briefly if no frame is available yet (waits up to 2 seconds).
        """
        for _ in range(20):
            with self._lock:
                if self._frames:
                    return self._frames[-1]
            time.sleep(0.1)
        # Fallback: take a one-shot screenshot synchronously
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
            img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
