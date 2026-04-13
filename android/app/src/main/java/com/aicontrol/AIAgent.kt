package com.aicontrol

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import com.google.ai.edge.aicore.GenerativeModel
import com.google.ai.edge.aicore.generationConfig
import com.google.ai.edge.aicore.content
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * On-device AI agent using Google AI Edge (Gemini Nano).
 *
 * The agent receives camera frames showing the computer screen and
 * decides what action to take next to complete the user's task. All
 * processing happens on-device — no network, no API key required.
 *
 * Requires: Android 14+, Pixel 8/9 series or Samsung Galaxy S24+.
 * The AICore service must be available (check [isAvailable]).
 */
class AIAgent(private val context: Context) {

    companion object {
        private const val TAG = "AIAgent"
        private const val MAX_ITERATIONS = 50

        private val SYSTEM_PROMPT = """
You are an AI agent controlling a computer remotely.
You see the computer screen through the phone's camera.
Use the available actions to complete the task step by step.

After each action you will receive a new camera frame showing the updated screen.
Always describe what you see before deciding what to do.

Reply with ONLY a single JSON object — no markdown, no explanation:

Move mouse:   {"type":"move","x":0.5,"y":0.3}        (x,y = 0.0 to 1.0 fraction of screen)
Left click:   {"type":"click","button":"left"}
Right click:  {"type":"click","button":"right"}
Double click: {"type":"dblclick"}
Scroll down:  {"type":"scroll","direction":"down","amount":3}
Scroll up:    {"type":"scroll","direction":"up","amount":3}
Type text:    {"type":"type","text":"hello world"}
Press key:    {"type":"key","key":"Return"}           (Return, Escape, Tab, ctrl+c, alt+F4, etc.)
Task done:    {"type":"done","message":"what was accomplished"}
""".trimIndent()
    }

    private var model: GenerativeModel? = null

    /**
     * Returns true if Gemini Nano (AICore) is available on this device.
     *
     * AICore requires Android 14+ on supported hardware (Pixel 8/9, Galaxy S24).
     * Wrapped in try/catch because the check itself may throw on unsupported devices.
     */
    fun isAvailable(): Boolean = try {
        // The AICore SDK exposes availability via a companion object check.
        // We also do a lightweight probe by attempting construction; if AICore
        // is missing the class won't load and we catch NoClassDefFoundError.
        val cls = Class.forName("com.google.ai.edge.aicore.GenerativeModel")
        val method = cls.getMethod("isAvailable", Context::class.java)
        method.invoke(null, context.applicationContext) as? Boolean ?: false
    } catch (e: Throwable) {
        false
    }

    /**
     * Initialize the Gemini Nano model.
     * Must be called after confirming [isAvailable] returns true.
     */
    fun init() {
        // Use applicationContext to avoid leaking the Activity.
        val appContext = context.applicationContext
        model = GenerativeModel(
            generationConfig = generationConfig {
                context = appContext
                temperature = 0.1f   // low temperature for deterministic, structured output
                topK = 16
                maxOutputTokens = 300
            }
        )
    }

    /**
     * Run an agent loop for [task].
     *
     * @param task         Natural language task description
     * @param camera       Camera controller supplying screen frames
     * @param hid          HID controller for executing mouse/keyboard actions
     * @param onStatus     Called with status updates (shown in app log)
     */
    suspend fun runTask(
        task: String,
        camera: CameraController,
        hid: HidController,
        onStatus: (String) -> Unit
    ) = withContext(Dispatchers.IO) {
        val m = model ?: run {
            onStatus("AI model not initialised. Call init() first.")
            return@withContext
        }

        onStatus("Starting task: $task")

        for (iteration in 1..MAX_ITERATIONS) {
            onStatus("[Step $iteration] Capturing screen...")

            // Capture current screen via camera
            val frame = camera.captureFrame(3000L)
            if (frame == null) {
                onStatus("Could not capture camera frame. Is the camera started?")
                return@withContext
            }
            val resized = camera.resize(frame, maxEdge = 1024)

            // Ask Gemini Nano what to do next
            val userPrompt = if (iteration == 1) {
                "Task: $task\n\nCurrent cursor is at approximately (${hid.cursorX * 100}%, ${hid.cursorY * 100}%) of the screen.\nWhat is the SINGLE next action?"
            } else {
                "Continue the task. Current cursor: (${hid.cursorX * 100}%, ${hid.cursorY * 100}%). What is the SINGLE next action?"
            }

            val rawResponse = try {
                m.generateContent(
                    content {
                        image(resized)
                        text("$SYSTEM_PROMPT\n\n$userPrompt")
                    }
                ).text ?: ""
            } catch (e: Exception) {
                Log.e(TAG, "AI generate failed: $e")
                onStatus("AI error: ${e.message}")
                return@withContext
            }

            Log.d(TAG, "AI raw response: $rawResponse")

            // Parse JSON action
            val action = parseAction(rawResponse.trim())
            if (action == null) {
                onStatus("Could not parse AI response: $rawResponse")
                continue
            }

            val actionType = action.optString("type", "")

            // Execute action
            when (actionType) {
                "move" -> {
                    val x = action.optDouble("x", 0.5).toFloat()
                    val y = action.optDouble("y", 0.5).toFloat()
                    onStatus("Moving mouse to (${(x*100).toInt()}%, ${(y*100).toInt()}%)")
                    hid.moveTo(x, y)
                }
                "click" -> {
                    val button = action.optString("button", "left")
                    onStatus("${button.replaceFirstChar { it.uppercase() }} click")
                    when (button) {
                        "left"   -> hid.leftClick()
                        "right"  -> hid.rightClick()
                        "middle" -> hid.middleClick()
                    }
                }
                "dblclick" -> {
                    onStatus("Double click")
                    hid.doubleClick()
                }
                "scroll" -> {
                    val dir = action.optString("direction", "down")
                    val amount = action.optInt("amount", 3)
                    onStatus("Scroll $dir ($amount)")
                    val scrollAmount = if (dir == "down") amount else -amount
                    hid.scroll(scrollAmount)
                }
                "type" -> {
                    val text = action.optString("text", "")
                    onStatus("Typing: \"$text\"")
                    hid.typeText(text)
                }
                "key" -> {
                    val key = action.optString("key", "")
                    onStatus("Key: $key")
                    hid.pressKeyCombo(key)
                }
                "done" -> {
                    val msg = action.optString("message", "Task complete.")
                    onStatus("Done: $msg")
                    return@withContext
                }
                else -> {
                    onStatus("Unknown action type: $actionType")
                }
            }

            // Small delay to let the computer's UI update
            Thread.sleep(500)
        }

        onStatus("Reached the maximum of $MAX_ITERATIONS steps.")
    }

    /**
     * Extract the first JSON object from the AI's raw text response.
     * The model sometimes wraps it in markdown code blocks.
     */
    private fun parseAction(raw: String): JSONObject? {
        // Strip markdown code fences if present
        val stripped = raw
            .removePrefix("```json").removePrefix("```")
            .removeSuffix("```")
            .trim()

        // Find first '{' ... '}'
        val start = stripped.indexOf('{')
        val end   = stripped.lastIndexOf('}')
        if (start < 0 || end <= start) return null

        return try {
            JSONObject(stripped.substring(start, end + 1))
        } catch (e: Exception) {
            Log.w(TAG, "JSON parse failed: $e  raw=$raw")
            null
        }
    }
}
