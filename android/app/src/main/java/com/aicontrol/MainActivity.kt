package com.aicontrol

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.inputmethod.EditorInfo
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

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: TaskViewModel by viewModels()

    private lateinit var hidController: HidController
    private lateinit var cameraController: CameraController
    private lateinit var aiAgent: AIAgent

    private val requestPermissions =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
            val denied = grants.filterValues { !it }.keys
            if (denied.isEmpty()) {
                startCamera()
                initHid()
            } else {
                toast("Permissions required: ${denied.joinToString()}")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        hidController  = HidController(this)
        cameraController = CameraController(this, this)
        aiAgent          = AIAgent(this)

        // Check AI availability
        if (!aiAgent.isAvailable()) {
            showAiUnavailableDialog()
        } else {
            aiAgent.init()
        }

        // HID connection state
        hidController.onConnectionChanged = { connected, name ->
            runOnUiThread {
                viewModel.setConnected(if (connected) name else null)
                if (connected) viewModel.addLog("HID connected to $name")
                else viewModel.addLog("HID disconnected")
            }
        }

        binding.btnConnect.setOnClickListener { onConnectClicked() }
        binding.btnSend.setOnClickListener { onRunClicked() }
        binding.etTask.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) { onRunClicked(); true } else false
        }

        // Observe ViewModel
        viewModel.connectionState.observe(this) { state ->
            val connected = state == ConnectionState.CONNECTED
            val name = viewModel.connectedDevice.value
            binding.tvStatusText.text = if (connected) "Connected to $name" else "Not connected — pair phone as HID device"
            binding.tvStatusDot.setBackgroundResource(if (connected) R.drawable.circle_green else R.drawable.circle_red)
            binding.btnConnect.text = if (connected) "Disconnect" else "Connect"
            binding.btnSend.isEnabled = connected
        }

        viewModel.log.observe(this) { entries ->
            binding.tvLog.text = entries.takeLast(80).joinToString("\n")
            binding.scrollLog.post { binding.scrollLog.fullScroll(android.view.View.FOCUS_DOWN) }
        }

        viewModel.isRunning.observe(this) { running ->
            binding.btnSend.text = if (running) "Stop" else "Run"
            binding.etTask.isEnabled = !running
            binding.tvHint.visibility = if (running) android.view.View.GONE else android.view.View.VISIBLE
        }

        requestRequiredPermissions()
    }

    // ── Permissions ──────────────────────────────────────────────────────────

    private fun requestRequiredPermissions() {
        val needed = buildList {
            add(Manifest.permission.CAMERA)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                add(Manifest.permission.BLUETOOTH_CONNECT)
                add(Manifest.permission.BLUETOOTH_ADVERTISE)
            } else {
                add(Manifest.permission.BLUETOOTH)
                add(Manifest.permission.BLUETOOTH_ADMIN)
            }
        }.filter {
            ActivityCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (needed.isEmpty()) {
            startCamera()
            initHid()
        } else {
            requestPermissions.launch(needed.toTypedArray())
        }
    }

    // ── Camera ────────────────────────────────────────────────────────────────

    private fun startCamera() {
        cameraController.start(binding.cameraPreview)
        viewModel.addLog("Camera started. Point at computer screen.")
    }

    // ── Bluetooth HID ─────────────────────────────────────────────────────────

    private fun initHid() {
        val btManager = getSystemService(BluetoothManager::class.java)
        val adapter = btManager?.adapter
        if (adapter == null || !adapter.isEnabled) {
            toast("Please enable Bluetooth.")
            return
        }
        hidController.register(adapter)
        viewModel.addLog("HID profile registered. Pair this phone from your computer's Bluetooth settings.")
    }

    private fun onConnectClicked() {
        if (hidController.isConnected) {
            hidController.unregister()
            viewModel.setConnected(null)
        } else {
            showConnectionInstructions()
        }
    }

    private fun showConnectionInstructions() {
        AlertDialog.Builder(this)
            .setTitle("How to connect")
            .setMessage(
                "1. On your COMPUTER, open Bluetooth settings\n" +
                "2. Search for new devices\n" +
                "3. Select \"AI Control\" from the list\n" +
                "4. Confirm the pairing on both devices\n\n" +
                "The phone will appear as a Bluetooth keyboard/mouse.\n" +
                "No software needed on the computer."
            )
            .setPositiveButton("OK", null)
            .show()
    }

    // ── AI Task ───────────────────────────────────────────────────────────────

    private fun onRunClicked() {
        if (viewModel.isRunning.value == true) {
            // TODO: cancellation — for now just log
            viewModel.addLog("Stopping after current step...")
            viewModel.setRunning(false)
            return
        }

        val task = binding.etTask.text?.toString()?.trim()
        if (task.isNullOrEmpty()) { toast("Enter a task first."); return }
        if (!hidController.isConnected) { toast("Not connected to a computer."); return }

        viewModel.clearLog()
        viewModel.setRunning(true)
        binding.etTask.setText("")

        lifecycleScope.launch(Dispatchers.IO) {
            // Configure HID screen resolution from user setting (could be a settings screen)
            // Default 1920x1080; user can adjust via a future settings screen.
            hidController.screenWidth  = 1920
            hidController.screenHeight = 1080

            aiAgent.runTask(
                task        = task,
                camera      = cameraController,
                hid         = hidController,
                onStatus    = { msg -> runOnUiThread { viewModel.addLog(msg) } }
            )

            runOnUiThread { viewModel.setRunning(false) }
        }
    }

    // ── AI availability dialog ────────────────────────────────────────────────

    private fun showAiUnavailableDialog() {
        AlertDialog.Builder(this)
            .setTitle("AI Not Available")
            .setMessage(
                "This app uses Google's on-device Gemini Nano AI (via AICore).\n\n" +
                "Supported devices:\n" +
                "• Google Pixel 8, 8 Pro, 8a, 9 series\n" +
                "• Samsung Galaxy S24 series\n\n" +
                "Your device does not appear to support AICore yet.\n" +
                "You can still use the app for HID keyboard/mouse control without AI."
            )
            .setPositiveButton("Continue anyway") { _, _ -> /* let user use HID manually */ }
            .setNegativeButton("Exit") { _, _ -> finish() }
            .show()
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    override fun onDestroy() {
        super.onDestroy()
        hidController.unregister()
    }
}
