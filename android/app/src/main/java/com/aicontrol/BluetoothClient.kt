package com.aicontrol

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.util.UUID

/**
 * Manages a Classic Bluetooth RFCOMM connection to the computer agent.
 *
 * All methods that touch the socket are intended to be called from a
 * background (IO) coroutine — they block and must not run on the main thread.
 */
class BluetoothClient {

    // Serial Port Profile UUID — must match the Python server.
    private val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

    private var socket: BluetoothSocket? = null
    private var writer: PrintWriter? = null
    private var reader: BufferedReader? = null

    val isConnected: Boolean
        get() = socket?.isConnected == true

    /**
     * Connect to [device]. Blocks until connected or throws on failure.
     */
    fun connect(device: BluetoothDevice) {
        disconnect()
        val sock = device.createRfcommSocketToServiceRecord(SPP_UUID)
        sock.connect()
        socket = sock
        writer = PrintWriter(sock.outputStream, /* autoFlush= */ true)
        reader = BufferedReader(InputStreamReader(sock.inputStream))
    }

    /**
     * Send a task string to the computer agent.
     */
    fun sendTask(task: String) {
        val json = JSONObject().apply {
            put("type", "task")
            put("text", task)
        }
        writer?.println(json.toString())
    }

    /**
     * Block and yield each status JSON object received from the computer.
     * Returns when the connection drops or the socket is closed.
     */
    fun readStatusUpdates(onUpdate: (JSONObject) -> Unit) {
        try {
            reader?.forEachLine { line ->
                val trimmed = line.trim()
                if (trimmed.isNotEmpty()) {
                    try {
                        onUpdate(JSONObject(trimmed))
                    } catch (_: Exception) {
                        // Ignore malformed JSON lines
                    }
                }
            }
        } catch (_: Exception) {
            // Connection dropped — caller will detect isConnected == false
        }
    }

    /**
     * Close the connection cleanly.
     */
    fun disconnect() {
        try { reader?.close() } catch (_: Exception) {}
        try { writer?.close() } catch (_: Exception) {}
        try { socket?.close() } catch (_: Exception) {}
        socket = null
        writer = null
        reader = null
    }
}
