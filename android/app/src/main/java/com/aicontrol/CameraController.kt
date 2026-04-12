package com.aicontrol

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.util.concurrent.Executors

/**
 * Wraps CameraX to show a live preview and capture frames for the AI.
 *
 * The back camera is pointed at the computer screen. Each captured frame
 * is passed to the AI agent as a Bitmap so it can understand what's on screen.
 */
class CameraController(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner
) {
    companion object {
        private const val TAG = "CameraController"
    }

    private val executor = Executors.newSingleThreadExecutor()
    private var latestBitmap: Bitmap? = null
    private val bitmapLock = Any()

    /**
     * Start the camera preview in [previewView] and begin capturing frames.
     * Each frame is stored and accessible via [latestFrame].
     */
    fun start(previewView: PreviewView) {
        val providerFuture = ProcessCameraProvider.getInstance(context)
        providerFuture.addListener({
            val provider = providerFuture.get()

            val preview = Preview.Builder()
                .build()
                .also { it.setSurfaceProvider(previewView.surfaceProvider) }

            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()

            imageAnalysis.setAnalyzer(executor) { imageProxy ->
                val bmp = imageProxy.toBitmap()
                synchronized(bitmapLock) { latestBitmap = bmp }
                imageProxy.close()
            }

            try {
                provider.unbindAll()
                provider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageAnalysis
                )
                Log.i(TAG, "Camera started")
            } catch (e: Exception) {
                Log.e(TAG, "Camera bind failed: $e")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    /**
     * Returns the most recently captured frame, rotated upright.
     * Returns null if no frame has been captured yet.
     */
    fun latestFrame(): Bitmap? {
        val bmp = synchronized(bitmapLock) { latestBitmap } ?: return null
        // Ensure the bitmap is in standard portrait/landscape orientation
        return if (bmp.width > 0 && bmp.height > 0) bmp else null
    }

    /**
     * Capture the current frame and return it.
     * Blocks up to [timeoutMs] ms waiting for the first frame.
     */
    fun captureFrame(timeoutMs: Long = 3000L): Bitmap? {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            val bmp = latestFrame()
            if (bmp != null) return bmp
            Thread.sleep(100)
        }
        return null
    }

    /** Scale [bmp] so the longest edge is at most [maxEdge] pixels. */
    fun resize(bmp: Bitmap, maxEdge: Int = 1024): Bitmap {
        val scale = minOf(1f, maxEdge.toFloat() / maxOf(bmp.width, bmp.height))
        if (scale >= 1f) return bmp
        val newW = (bmp.width * scale).toInt()
        val newH = (bmp.height * scale).toInt()
        return Bitmap.createScaledBitmap(bmp, newW, newH, true)
    }
}
