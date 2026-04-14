package com.moviegenerator

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

private val SYSTEM_PROMPT = """
You are an expert Three.js JavaScript 3D animation developer for a mobile movie generator app.

When the user describes a movie they want, respond with:
1. ONE short sentence describing what you will create.
2. A complete JavaScript snippet inside a ```javascript ... ``` code block.

━━━━━━━  MANDATORY CODE REQUIREMENTS  ━━━━━━━
The script runs inside a Three.js r158 WebGL context where `THREE`, `scene`,
`camera`, and a WebGLRenderer are already set up at 720×1280 portrait.

Your code MUST define exactly these three things:

  const TOTAL_FRAMES = <integer>;          // frames at 24 fps, e.g. 10 s = 240

  function initScene(THREE, scene, camera) {
    // Create objects, lights, materials.  Store them in module-scope variables.
    scene.background = new THREE.Color(0x000010);  // example — always set bg
  }

  function updateScene(frameNum, THREE, scene, camera) {
    // Animate for frame `frameNum` (0 … TOTAL_FRAMES-1).
    // Update positions, rotations, colors, etc.
  }

Rules:
• Use ONLY Three.js r158 API — THREE is already in scope, no imports needed.
• Declare shared objects (meshes, lights, etc.) with let/const at the top of
  the code block so both initScene and updateScene can access them.
• Always add at least AmbientLight + DirectionalLight.
• Use MeshStandardMaterial or MeshPhongMaterial for visible objects.
• Do NOT use any loader, external texture URL, or require().
• Keep code self-contained and runnable — no syntax errors.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".trimIndent()

class GptClient(private val apiKey: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    private val history = mutableListOf<JSONObject>()

    /** Returns Pair(animationCode, shortDescription) or throws on error. */
    fun generateAnimation(userRequest: String): Pair<String, String> {
        history.add(userMessage("Create a movie for me: $userRequest"))
        val reply = chat()
        val code = extractCode(reply) ?: error("No JavaScript code block found in GPT reply.")
        val desc = extractDescription(reply)
        return Pair(code, desc)
    }

    fun fixAnimation(brokenCode: String, errorMsg: String): Pair<String, String> {
        val fix = "The Three.js code failed:\n\n```\n${errorMsg.take(1500)}\n```\n\n" +
                "Original code:\n```javascript\n$brokenCode\n```\n\nPlease fix it."
        history.add(userMessage(fix))
        val reply = chat()
        val code = extractCode(reply) ?: error("No code block in fix reply.")
        val desc = extractDescription(reply)
        return Pair(code, desc)
    }

    fun reset() = history.clear()

    // ── private ───────────────────────────────────────────────────────────────

    private fun chat(): String {
        val messages = JSONArray().apply {
            put(JSONObject().put("role", "system").put("content", SYSTEM_PROMPT))
            history.forEach { put(it) }
        }
        val body = JSONObject()
            .put("model", "gpt-4o")
            .put("messages", messages)
            .put("temperature", 0.7)
            .put("max_tokens", 4096)
            .toString()
            .toRequestBody("application/json".toMediaType())

        val req = Request.Builder()
            .url("https://api.openai.com/v1/chat/completions")
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        val response = client.newCall(req).execute()
        val responseBody = response.body?.string() ?: error("Empty response from OpenAI")
        if (!response.isSuccessful) error("OpenAI error ${response.code}: $responseBody")

        val content = JSONObject(responseBody)
            .getJSONArray("choices")
            .getJSONObject(0)
            .getJSONObject("message")
            .getString("content")

        history.add(JSONObject().put("role", "assistant").put("content", content))
        return content
    }

    private fun userMessage(text: String) =
        JSONObject().put("role", "user").put("content", text)

    private fun extractCode(text: String): String? {
        val patterns = listOf(
            Regex("```javascript\\s*(.*?)\\s*```", RegexOption.DOT_MATCHES_ALL),
            Regex("```js\\s*(.*?)\\s*```", RegexOption.DOT_MATCHES_ALL),
            Regex("```\\s*(.*?)\\s*```", RegexOption.DOT_MATCHES_ALL),
        )
        for (p in patterns) {
            val m = p.find(text)
            if (m != null) {
                val code = m.groupValues[1].trim()
                if ("TOTAL_FRAMES" in code) return code
            }
        }
        return null
    }

    private fun extractDescription(text: String): String {
        val clean = text.replace(Regex("```.*?```", RegexOption.DOT_MATCHES_ALL), "").trim()
        return clean.lines().firstOrNull { it.isNotBlank() }?.trim() ?: "Generating your movie…"
    }
}
