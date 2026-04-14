package com.moviegenerator

import android.content.ContentValues
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class RendererActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "RendererActivity"
        private const val RENDER_W = 720
        private const val RENDER_H = 1280
        private const val FPS = 24
    }

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvStatus: TextView

    private var totalFrames = 0
    private var framesEncoded = 0
    private var encoder: VideoEncoder? = null
    private var outputFile: File? = null
    private var jsCode: String = ""
    private var renderError: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_renderer)

        jsCode = intent.getStringExtra("js_code") ?: run { finish(); return }

        webView     = findViewById(R.id.webView)
        progressBar = findViewById(R.id.renderProgress)
        tvStatus    = findViewById(R.id.tvStatus)

        setupWebView()
        loadRenderer()
    }

    // ── WebView setup ─────────────────────────────────────────────────────────

    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_NO_CACHE
        }
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient   = WebViewClient()
        webView.addJavascriptInterface(AndroidBridge(), "Android")
    }

    private fun loadRenderer() {
        // Read renderer.html template and inject the GPT-generated code
        val template = assets.open("renderer.html").bufferedReader().readText()
        val html = template.replace("// @@ANIMATION_CODE@@", jsCode)
        webView.loadDataWithBaseURL(
            "https://cdn.jsdelivr.net",   // allow CDN resources (Three.js)
            html, "text/html", "utf-8", null
        )
        tvStatus.text = "Loading Three.js engine…"
    }

    // ── JavaScript bridge (called from renderer.html) ─────────────────────────

    inner class AndroidBridge {

        @JavascriptInterface
        fun onRendererReady(frames: Int) {
            Log.d(TAG, "Renderer ready, totalFrames=$frames")
            totalFrames   = frames
            framesEncoded = 0
            renderError   = null

            runOnUiThread {
                progressBar.max      = frames
                progressBar.progress = 0
                tvStatus.text        = "Rendering frame 0 / $frames…"
            }

            // Create output file
            val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            outputFile = getOutputFile("movie_$stamp.mp4")
            encoder = VideoEncoder(RENDER_W, RENDER_H, FPS, outputFile!!)

            // Kick off rendering
            webView.post { webView.evaluateJavascript("window.renderFrame(0)", null) }
        }

        @JavascriptInterface
        fun onFrameCaptured(frameNum: Int, base64Jpeg: String) {
            if (renderError != null) return   // already failed

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val bytes = Base64.decode(base64Jpeg, Base64.DEFAULT)
                    val bmp   = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        ?: throw IllegalStateException("Could not decode frame $frameNum")

                    // Scale to exact render dimensions just in case WebView reported different
                    val scaled = if (bmp.width != RENDER_W || bmp.height != RENDER_H)
                        Bitmap.createScaledBitmap(bmp, RENDER_W, RENDER_H, true) else bmp

                    encoder!!.encodeFrame(scaled)
                    framesEncoded++

                    withContext(Dispatchers.Main) {
                        progressBar.progress = framesEncoded
                        tvStatus.text = "Rendering frame $framesEncoded / $totalFrames…"
                    }

                    if (framesEncoded >= totalFrames) {
                        finishEncoding()
                    } else {
                        withContext(Dispatchers.Main) {
                            webView.evaluateJavascript("window.renderFrame($framesEncoded)", null)
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Frame encode error", e)
                    handleError("Frame $frameNum encode error: ${e.message}")
                }
            }
        }

        @JavascriptInterface
        fun onRenderError(message: String) {
            Log.e(TAG, "JS render error: $message")
            handleError(message)
        }
    }

    // ── Completion & error ────────────────────────────────────────────────────

    private suspend fun finishEncoding() {
        withContext(Dispatchers.IO) { encoder?.finish() }
        val path = outputFile?.absolutePath ?: "unknown"

        // Add to MediaStore so it appears in gallery / Files app
        addToMediaStore(outputFile!!)

        withContext(Dispatchers.Main) {
            tvStatus.text = "Done!"
            progressBar.visibility = View.INVISIBLE

            AlertDialog.Builder(this@RendererActivity)
                .setTitle("Movie ready!")
                .setMessage("Saved to:\n$path")
                .setPositiveButton("Great!") { _, _ -> finish() }
                .setCancelable(false)
                .show()
        }
    }

    private fun handleError(msg: String) {
        if (renderError != null) return
        renderError = msg
        encoder?.runCatching { finish() }

        runOnUiThread {
            AlertDialog.Builder(this)
                .setTitle("Render error")
                .setMessage(msg)
                .setPositiveButton("Go back") { _, _ -> finish() }
                .show()
        }
    }

    private fun addToMediaStore(file: File) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Video.Media.DISPLAY_NAME, file.name)
                put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
                put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES)
            }
            contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)
        }
    }

    private fun getOutputFile(name: String): File {
        val dir = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            getExternalFilesDir(Environment.DIRECTORY_MOVIES)
                ?: filesDir
        } else {
            @Suppress("DEPRECATION")
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES)
        }
        dir!!.mkdirs()
        return File(dir, name)
    }

    override fun onBackPressed() {
        if (framesEncoded < totalFrames && encoder != null) {
            AlertDialog.Builder(this)
                .setTitle("Cancel rendering?")
                .setMessage("The movie is still being rendered. Cancel and go back?")
                .setPositiveButton("Cancel render") { _, _ ->
                    encoder?.runCatching { finish() }
                    super.onBackPressed()
                }
                .setNegativeButton("Keep going", null)
                .show()
        } else {
            super.onBackPressed()
        }
    }
}
