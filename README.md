# AI Computer Control

Control any computer with your Android phone — **no software needed on the computer at all.**

```
  PHONE                               COMPUTER
  ┌──────────────────────┐            ┌──────────────────┐
  │ 📷 Camera sees       │            │                  │
  │    computer screen   │            │  Nothing needed. │
  │                      │            │  Phone pairs as  │
  │ 🤖 Gemini Nano AI    │──Bluetooth─▶  a standard BT   │
  │    decides what to do│            │  keyboard+mouse  │
  │                      │            │                  │
  │ ⌨️  Sends keystrokes │            │  Any OS works:   │
  │    and mouse clicks  │            │  Windows, Mac,   │
  └──────────────────────┘            │  Linux, ChromeOS │
                                      └──────────────────┘
```

The phone acts exactly like a Bluetooth keyboard and mouse — every OS supports this out of the box, no drivers needed.

---

## Download

**[Download AIControl.apk](https://github.com/gge2898/Geremoah/releases/latest/download/AIControl.apk)**

Install: open the APK → tap Install → allow "Install from unknown sources" if prompted.

---

## Requirements

| What | Minimum |
|---|---|
| Android version | Android 9 (API 28) |
| For AI features | Android 14+ on Pixel 8/9 or Galaxy S24 series |
| Computer | Any computer with Bluetooth — nothing to install |

---

## How to use

### 1. Pair the phone with the computer (one time)
On the **computer**, open Bluetooth settings → search for devices → select **"AI Control"**.
Confirm the pairing on both devices. That's it — the phone now appears as a Bluetooth input device.

### 2. Position the phone camera
Point the back camera at the computer screen so the AI can see what's on it.
A stand or leaning the phone against something works well.

### 3. Type a task and tap Run
The AI watches the live camera feed, figures out where to click and what to type,
and controls the computer via Bluetooth — exactly as if you were using a wireless keyboard and mouse.

---

## Example tasks

| Task | What happens |
|---|---|
| `open firefox and go to google.com` | AI finds Firefox, clicks it, types the URL |
| `open the terminal` | AI presses keyboard shortcut or clicks the terminal icon |
| `type "hello world" in the text editor` | AI clicks the editor and types |
| `press ctrl+z three times` | AI sends the keyboard shortcut |
| `close this window` | AI presses Alt+F4 or clicks the close button |

---

## How it works

1. **Bluetooth HID** — Android's `BluetoothHidDevice` API lets the phone register itself as a standard keyboard + mouse. The computer's OS handles this natively (same protocol as any Bluetooth keyboard/mouse).

2. **Camera feed** — CameraX streams the back camera at 5 FPS. The AI sees what's on the computer screen in real time.

3. **On-device AI** — Google AI Edge SDK (Gemini Nano) runs entirely on the phone. No internet connection needed, no API key, no cloud.

4. **Agent loop** — The AI sees the screen, decides one action (move mouse, click, type, press key), executes it, then sees the updated screen and decides the next action.

---

## Project structure

```
android/
└── app/src/main/java/com/aicontrol/
    ├── MainActivity.kt        Camera preview + task input UI
    ├── HidController.kt       Bluetooth HID (keyboard + mouse)
    ├── CameraController.kt    CameraX live frame capture
    ├── AIAgent.kt             Gemini Nano agent loop
    └── TaskViewModel.kt       State management
```

The `computer_agent/` folder contains an optional Python-based alternative
for computers where you're OK running a small agent script. For the true
zero-install experience, the Android app alone is all you need.
