package com.aicontrol

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.lifecycle.lifecycleScope
import com.aicontrol.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: TaskViewModel by viewModels()

    private val btClient = BluetoothClient()
    private var bluetoothAdapter: BluetoothAdapter? = null

    // Permission request launcher
    private val requestPermissions =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
            if (grants.values.all { it }) showDevicePicker()
            else toast("Bluetooth permission denied.")
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val btManager = getSystemService(BluetoothManager::class.java)
        bluetoothAdapter = btManager?.adapter

        if (bluetoothAdapter == null) {
            toast("This device does not support Bluetooth.")
            binding.btnConnect.isEnabled = false
        }

        binding.btnConnect.setOnClickListener { onConnectClicked() }
        binding.btnSend.setOnClickListener { onSendClicked() }

        // Observe ViewModel state
        viewModel.isConnected.observe(this) { connected ->
            val deviceName = viewModel.connectedDevice.value
            if (connected && deviceName != null) {
                binding.tvStatus.text = "Connected to $deviceName"
                binding.tvStatus.setTextColor(getColor(R.color.status_done))
                binding.btnSend.isEnabled = true
                binding.btnConnect.text = "Disconnect"
            } else {
                binding.tvStatus.text = "Not connected"
                binding.tvStatus.setTextColor(getColor(R.color.status_error))
                binding.btnSend.isEnabled = false
                binding.btnConnect.text = "Connect to Computer"
            }
        }

        viewModel.log.observe(this) { entries ->
            val sb = StringBuilder()
            for (entry in entries) {
                sb.appendLine(formatLogEntry(entry))
            }
            binding.tvLog.text = sb
            // Auto-scroll to bottom
            binding.scrollLog.post { binding.scrollLog.fullScroll(android.view.View.FOCUS_DOWN) }
        }
    }

    private fun onConnectClicked() {
        if (btClient.isConnected) {
            disconnectBluetooth()
            return
        }

        val requiredPerms = buildList {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                add(Manifest.permission.BLUETOOTH_CONNECT)
                add(Manifest.permission.BLUETOOTH_SCAN)
            } else {
                add(Manifest.permission.BLUETOOTH)
                add(Manifest.permission.BLUETOOTH_ADMIN)
            }
        }.filter { ActivityCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }

        if (requiredPerms.isEmpty()) showDevicePicker()
        else requestPermissions.launch(requiredPerms.toTypedArray())
    }

    private fun showDevicePicker() {
        val adapter = bluetoothAdapter ?: return

        if (!adapter.isEnabled) {
            toast("Please enable Bluetooth first.")
            return
        }

        val pairedDevices: Set<BluetoothDevice> = try {
            adapter.bondedDevices ?: emptySet()
        } catch (e: SecurityException) {
            toast("Bluetooth permission needed.")
            return
        }

        if (pairedDevices.isEmpty()) {
            toast("No paired Bluetooth devices found. Pair your computer first in Settings → Bluetooth.")
            return
        }

        val names = pairedDevices.map { it.name ?: it.address }.toTypedArray()
        val devices = pairedDevices.toList()

        AlertDialog.Builder(this)
            .setTitle("Select Computer")
            .setItems(names) { _, index -> connectToDevice(devices[index]) }
            .show()
    }

    private fun connectToDevice(device: BluetoothDevice) {
        binding.tvStatus.text = "Connecting…"
        binding.tvStatus.setTextColor(Color.YELLOW)
        binding.btnConnect.isEnabled = false

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                btClient.connect(device)
                val name = try { device.name } catch (_: SecurityException) { device.address }
                withContext(Dispatchers.Main) {
                    viewModel.setConnected(name)
                    viewModel.clearLog()
                    binding.btnConnect.isEnabled = true
                    appendLog("system", "Connected to $name. Enter a task below.")
                }
                // Start reading status updates
                btClient.readStatusUpdates { json -> handleStatusUpdate(json) }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.btnConnect.isEnabled = true
                    viewModel.setConnected(null)
                    toast("Connection failed: ${e.message}")
                }
            }
            // Connection ended
            withContext(Dispatchers.Main) {
                viewModel.setConnected(null)
                appendLog("system", "Disconnected.")
            }
        }
    }

    private fun handleStatusUpdate(json: JSONObject) {
        val type = json.optString("type", "info")
        val text = when (type) {
            "thinking" -> json.optString("message", "")
            "action"   -> buildActionText(json)
            "done"     -> json.optString("message", "Task complete.")
            "error"    -> json.optString("message", "Unknown error.")
            else       -> json.toString()
        }
        lifecycleScope.launch(Dispatchers.Main) {
            appendLog(type, text)
        }
    }

    private fun buildActionText(json: JSONObject): String {
        val action = json.optString("action", "?")
        val parts = mutableListOf<String>()
        json.keys().forEach { key ->
            if (key != "type" && key != "action") {
                parts.add("$key=${json.opt(key)}")
            }
        }
        return if (parts.isEmpty()) action else "$action(${parts.joinToString(", ")})"
    }

    private fun appendLog(type: String, text: String) {
        viewModel.appendLog(LogEntry(type, text))
    }

    private fun formatLogEntry(entry: LogEntry): String {
        val prefix = when (entry.type) {
            "thinking" -> "[AI] "
            "action"   -> "[→]  "
            "done"     -> "[✓]  "
            "error"    -> "[!]  "
            "system"   -> "[*]  "
            else       -> "     "
        }
        return "$prefix${entry.text}"
    }

    private fun onSendClicked() {
        val task = binding.etTask.text?.toString()?.trim() ?: return
        if (task.isEmpty()) {
            toast("Please enter a task.")
            return
        }
        if (!btClient.isConnected) {
            toast("Not connected. Tap 'Connect to Computer' first.")
            return
        }

        appendLog("system", "Sending: $task")
        binding.etTask.setText("")

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                btClient.sendTask(task)
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    toast("Failed to send: ${e.message}")
                }
            }
        }
    }

    private fun disconnectBluetooth() {
        btClient.disconnect()
        viewModel.setConnected(null)
        appendLog("system", "Disconnected.")
    }

    private fun toast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    override fun onDestroy() {
        super.onDestroy()
        btClient.disconnect()
    }
}
