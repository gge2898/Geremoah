package com.aicontrol

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.util.Log
import java.util.concurrent.Executors

/**
 * Registers the phone as a Bluetooth HID device (keyboard + mouse).
 *
 * The computer pairs with the phone exactly like any Bluetooth keyboard or mouse —
 * no software, no drivers, no installation required on the computer side.
 *
 * Usage:
 *   1. hidController.register()
 *   2. Connect from computer's Bluetooth settings (phone appears as "AI Control")
 *   3. hidController.moveTo(0.5f, 0.3f)  // move cursor to 50% x, 30% y
 *   4. hidController.leftClick()
 *   5. hidController.typeText("hello world")
 */
class HidController(private val context: Context) {

    companion object {
        private const val TAG = "HidController"

        // Report IDs — must match the descriptor below
        const val MOUSE_REPORT_ID: Byte = 1
        const val KEYBOARD_REPORT_ID: Byte = 2

        // Combined HID report descriptor: relative mouse (report 1) + keyboard (report 2)
        val HID_DESCRIPTOR = byteArrayOf(
            // ── Mouse (Report ID 1) ───────────────────────────────────────
            0x05, 0x01,       // Usage Page (Generic Desktop)
            0x09, 0x02,       // Usage (Mouse)
            0xA1.toByte(), 0x01, // Collection (Application)
            0x85.toByte(), 0x01, //   Report ID (1)
            0x09, 0x01,       //   Usage (Pointer)
            0xA1.toByte(), 0x00, //   Collection (Physical)
            0x05, 0x09,       //     Usage Page (Button)
            0x19, 0x01,       //     Usage Minimum (1)
            0x29, 0x05,       //     Usage Maximum (5)
            0x15, 0x00,       //     Logical Minimum (0)
            0x25, 0x01,       //     Logical Maximum (1)
            0x95.toByte(), 0x05, //     Report Count (5)
            0x75, 0x01,       //     Report Size (1)
            0x81.toByte(), 0x02, //     Input (Data, Var, Abs) — buttons
            0x95.toByte(), 0x01, //     Report Count (1)
            0x75, 0x03,       //     Report Size (3) — padding
            0x81.toByte(), 0x01, //     Input (Const)
            0x05, 0x01,       //     Usage Page (Generic Desktop)
            0x09, 0x30,       //     Usage (X)
            0x09, 0x31,       //     Usage (Y)
            0x15, 0x81.toByte(), //   Logical Minimum (-127)
            0x25, 0x7F,       //     Logical Maximum (127)
            0x75, 0x08,       //     Report Size (8)
            0x95.toByte(), 0x02, //     Report Count (2) — X, Y
            0x81.toByte(), 0x06, //     Input (Data, Var, Rel)
            0x09, 0x38,       //     Usage (Wheel)
            0x15, 0x81.toByte(), //   Logical Minimum (-127)
            0x25, 0x7F,       //     Logical Maximum (127)
            0x75, 0x08,       //     Report Size (8)
            0x95.toByte(), 0x01, //     Report Count (1)
            0x81.toByte(), 0x06, //     Input (Data, Var, Rel) — wheel
            0xC0.toByte(),    //   End Collection (Physical)
            0xC0.toByte(),    // End Collection (Application)

            // ── Keyboard (Report ID 2) ────────────────────────────────────
            0x05, 0x01,       // Usage Page (Generic Desktop)
            0x09, 0x06,       // Usage (Keyboard)
            0xA1.toByte(), 0x01, // Collection (Application)
            0x85.toByte(), 0x02, //   Report ID (2)
            0x05, 0x07,       //   Usage Page (Keyboard/Keypad)
            0x19, 0xE0.toByte(), //   Usage Minimum (Left Ctrl = 0xE0)
            0x29, 0xE7.toByte(), //   Usage Maximum (Right GUI = 0xE7)
            0x15, 0x00,       //   Logical Minimum (0)
            0x25, 0x01,       //   Logical Maximum (1)
            0x75, 0x01,       //   Report Size (1)
            0x95.toByte(), 0x08, //   Report Count (8) — 8 modifier bits
            0x81.toByte(), 0x02, //   Input (Data, Var, Abs) — modifiers
            0x95.toByte(), 0x01, //   Report Count (1)
            0x75, 0x08,       //   Report Size (8) — reserved
            0x81.toByte(), 0x01, //   Input (Const)
            0x95.toByte(), 0x06, //   Report Count (6) — 6 simultaneous keys
            0x75, 0x08,       //   Report Size (8)
            0x15, 0x00,       //   Logical Minimum (0)
            0x26, 0xFF.toByte(), 0x00, // Logical Maximum (255)
            0x05, 0x07,       //   Usage Page (Keyboard/Keypad)
            0x19, 0x00,       //   Usage Minimum (0)
            0x29, 0xFF.toByte(), //   Usage Maximum (255)
            0x81.toByte(), 0x00, //   Input (Data, Array, Abs) — keycodes
            0xC0.toByte()     // End Collection
        )

        // Modifier key bitmasks
        const val MOD_LEFT_CTRL: Byte  = 0x01
        const val MOD_LEFT_SHIFT: Byte = 0x02
        const val MOD_LEFT_ALT: Byte   = 0x04
        const val MOD_LEFT_GUI: Byte   = 0x08  // Win / Cmd
        const val MOD_RIGHT_CTRL: Byte = 0x10
        const val MOD_RIGHT_SHIFT: Byte = 0x20
        const val MOD_RIGHT_ALT: Byte  = 0x40
        const val MOD_RIGHT_GUI: Byte  = 0x80.toByte()

        // HID keycodes for common keys
        val KEYCODE_MAP = mapOf(
            "Return"    to 0x28, "Enter"      to 0x28,
            "Escape"    to 0x29, "BackSpace"  to 0x2A,
            "Tab"       to 0x2B, "space"      to 0x2C,
            "Delete"    to 0x4C, "Insert"     to 0x49,
            "Home"      to 0x4A, "End"        to 0x4D,
            "PageUp"    to 0x4B, "PageDown"   to 0x4E,
            "Up"        to 0x52, "Down"       to 0x51,
            "Left"      to 0x50, "Right"      to 0x4F,
            "F1"  to 0x3A, "F2"  to 0x3B, "F3"  to 0x3C, "F4"  to 0x3D,
            "F5"  to 0x3E, "F6"  to 0x3F, "F7"  to 0x40, "F8"  to 0x41,
            "F9"  to 0x42, "F10" to 0x43, "F11" to 0x44, "F12" to 0x45,
            "ctrl"  to -1, "shift" to -2, "alt" to -3, "super" to -4,
            "win"   to -4, "cmd"   to -4,
        )

        // US keyboard layout: char → (HID keycode, shift?)
        val CHAR_MAP: Map<Char, Pair<Int, Boolean>> = buildMap {
            ('a'..'z').forEach { put(it, Pair(0x04 + (it - 'a'), false)) }
            ('A'..'Z').forEach { put(it, Pair(0x04 + (it - 'A'), true)) }
            ('1'..'9').forEach { put(it, Pair(0x1E + (it - '1'), false)) }
            put('0', Pair(0x27, false))
            put(' ', Pair(0x2C, false)); put('\n', Pair(0x28, false))
            put('\t', Pair(0x2B, false)); put('\b', Pair(0x2A, false))
            put('!', Pair(0x1E, true));  put('@', Pair(0x1F, true))
            put('#', Pair(0x20, true));  put('$', Pair(0x21, true))
            put('%', Pair(0x22, true));  put('^', Pair(0x23, true))
            put('&', Pair(0x24, true));  put('*', Pair(0x25, true))
            put('(', Pair(0x26, true));  put(')', Pair(0x27, true))
            put('-', Pair(0x2D, false)); put('_', Pair(0x2D, true))
            put('=', Pair(0x2E, false)); put('+', Pair(0x2E, true))
            put('[', Pair(0x2F, false)); put('{', Pair(0x2F, true))
            put(']', Pair(0x30, false)); put('}', Pair(0x30, true))
            put('\\', Pair(0x31, false));put('|', Pair(0x31, true))
            put(';', Pair(0x33, false)); put(':', Pair(0x33, true))
            put('\'', Pair(0x34, false));put('"', Pair(0x34, true))
            put('`', Pair(0x35, false)); put('~', Pair(0x35, true))
            put(',', Pair(0x36, false)); put('<', Pair(0x36, true))
            put('.', Pair(0x37, false)); put('>', Pair(0x37, true))
            put('/', Pair(0x38, false)); put('?', Pair(0x38, true))
        }
    }

    private var hidDevice: BluetoothHidDevice? = null
    private var connectedHost: BluetoothDevice? = null
    private val executor = Executors.newSingleThreadExecutor()

    // Virtual cursor position as fraction of screen (0.0–1.0)
    var cursorX: Float = 0.5f; private set
    var cursorY: Float = 0.5f; private set

    // Estimated computer screen size in pixels (user-configurable)
    var screenWidth: Int = 1920
    var screenHeight: Int = 1080

    var onConnectionChanged: ((Boolean, String) -> Unit)? = null

    private val hidCallback = object : BluetoothHidDevice.Callback() {
        override fun onConnectionStateChanged(device: BluetoothDevice, state: Int) {
            if (state == BluetoothProfile.STATE_CONNECTED) {
                connectedHost = device
                onConnectionChanged?.invoke(true, device.name ?: device.address)
                Log.i(TAG, "HID connected to ${device.name}")
            } else if (state == BluetoothProfile.STATE_DISCONNECTED) {
                connectedHost = null
                onConnectionChanged?.invoke(false, "")
                Log.i(TAG, "HID disconnected")
            }
        }
        override fun onGetReport(device: BluetoothDevice, type: Byte, id: Byte, bufferSize: Int) {}
        override fun onSetReport(device: BluetoothDevice, type: Byte, id: Byte, data: ByteArray) {}
    }

    fun register(bluetoothAdapter: android.bluetooth.BluetoothAdapter) {
        val sdp = BluetoothHidDeviceAppSdpSettings(
            "AI Control",
            "AI Computer Controller",
            "AIControl",
            BluetoothHidDevice.SUBCLASS1_COMBO,
            HID_DESCRIPTOR
        )
        bluetoothAdapter.getProfileProxy(context, object : BluetoothProfile.ServiceListener {
            override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
                hidDevice = proxy as BluetoothHidDevice
                hidDevice?.registerApp(sdp, null, null, executor, hidCallback)
                Log.i(TAG, "HID service connected, app registered")
            }
            override fun onServiceDisconnected(profile: Int) {
                hidDevice = null
            }
        }, BluetoothProfile.HID_DEVICE)
    }

    fun unregister() {
        hidDevice?.unregisterApp()
    }

    val isConnected: Boolean get() = connectedHost != null

    // ── Mouse ──────────────────────────────────────────────────────────────

    /** Move cursor to (xFraction, yFraction) of the computer screen (0.0–1.0). */
    fun moveTo(xFraction: Float, yFraction: Float) {
        val targetX = (xFraction.coerceIn(0f, 1f) * screenWidth).toInt()
        val targetY = (yFraction.coerceIn(0f, 1f) * screenHeight).toInt()
        val curX = (cursorX * screenWidth).toInt()
        val curY = (cursorY * screenHeight).toInt()
        sendRelativeMouseMove(targetX - curX, targetY - curY)
        cursorX = xFraction.coerceIn(0f, 1f)
        cursorY = yFraction.coerceIn(0f, 1f)
    }

    private fun sendRelativeMouseMove(totalDx: Int, totalDy: Int) {
        var remainX = totalDx; var remainY = totalDy
        while (remainX != 0 || remainY != 0) {
            val dx = remainX.coerceIn(-127, 127)
            val dy = remainY.coerceIn(-127, 127)
            sendMouseReport(0, dx.toByte(), dy.toByte(), 0)
            remainX -= dx; remainY -= dy
            Thread.sleep(8)
        }
    }

    fun leftClick()  = pressAndReleaseMouse(1)
    fun rightClick() = pressAndReleaseMouse(2)
    fun middleClick() = pressAndReleaseMouse(4)

    fun doubleClick() {
        leftClick(); Thread.sleep(80); leftClick()
    }

    fun scroll(amount: Int) {
        // positive = down, negative = up; clamped to HID range
        sendMouseReport(0, 0, 0, amount.coerceIn(-127, 127).toByte())
    }

    private fun pressAndReleaseMouse(buttonMask: Int) {
        sendMouseReport(buttonMask.toByte(), 0, 0, 0)
        Thread.sleep(50)
        sendMouseReport(0, 0, 0, 0)
    }

    private fun sendMouseReport(buttons: Byte, dx: Byte, dy: Byte, wheel: Byte) {
        val host = connectedHost ?: return
        hidDevice?.sendReport(host, MOUSE_REPORT_ID.toInt(),
            byteArrayOf(buttons, dx, dy, wheel))
    }

    // ── Keyboard ───────────────────────────────────────────────────────────

    /** Type a string one character at a time. */
    fun typeText(text: String) {
        for (ch in text) {
            val entry = CHAR_MAP[ch] ?: continue
            val (code, shift) = entry
            val mod = if (shift) MOD_LEFT_SHIFT else 0
            pressKey(mod.toInt(), code)
            Thread.sleep(30)
        }
    }

    /**
     * Press a key combo string like "ctrl+c", "Return", "alt+F4".
     * Tokens are split on '+', modifier names are recognised specially.
     */
    fun pressKeyCombo(combo: String) {
        val parts = combo.trim().split("+").map { it.trim() }
        var modifiers = 0
        val keycodes = mutableListOf<Int>()

        for (part in parts) {
            when (part.lowercase()) {
                "ctrl"  -> modifiers = modifiers or 0x01
                "shift" -> modifiers = modifiers or 0x02
                "alt"   -> modifiers = modifiers or 0x04
                "win", "super", "cmd" -> modifiers = modifiers or 0x08
                else -> {
                    val code = KEYCODE_MAP[part] ?: KEYCODE_MAP[part.lowercase()]
                    if (code != null && code > 0) keycodes.add(code)
                    else {
                        // Single character key
                        val entry = CHAR_MAP[part.firstOrNull() ?: ' ']
                        if (entry != null) {
                            if (entry.second) modifiers = modifiers or 0x02 // shift
                            keycodes.add(entry.first)
                        }
                    }
                }
            }
        }
        pressKey(modifiers, keycodes.firstOrNull() ?: 0)
    }

    private fun pressKey(modifiers: Int, keycode: Int) {
        val host = connectedHost ?: return
        val report = ByteArray(8)
        report[0] = modifiers.toByte()
        report[1] = 0  // reserved
        if (keycode > 0) report[2] = keycode.toByte()
        hidDevice?.sendReport(host, KEYBOARD_REPORT_ID.toInt(), report)
        Thread.sleep(50)
        hidDevice?.sendReport(host, KEYBOARD_REPORT_ID.toInt(), ByteArray(8)) // key-up
    }
}
