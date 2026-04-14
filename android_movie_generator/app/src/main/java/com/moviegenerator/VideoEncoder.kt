package com.moviegenerator

import android.graphics.Bitmap
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.util.Log
import java.io.File
import java.nio.ByteBuffer

/**
 * Encodes a sequence of Bitmap frames into an H.264/MP4 file.
 * Call [encodeFrame] for each frame in order, then [finish] to close the file.
 */
class VideoEncoder(
    private val width: Int,
    private val height: Int,
    private val fps: Int,
    outputFile: File
) {
    private val codec: MediaCodec
    private val muxer: MediaMuxer
    private val bufferInfo = MediaCodec.BufferInfo()
    private var trackIndex = -1
    private var muxerStarted = false
    private var presentationUs = 0L

    init {
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar)
            setInteger(MediaFormat.KEY_BIT_RATE, 4_000_000)   // 4 Mbps
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        }
        codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        codec.start()
        muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
    }

    fun encodeFrame(bitmap: Bitmap) {
        val yuv = bitmapToNV21(bitmap)
        val idx = codec.dequeueInputBuffer(10_000)
        if (idx >= 0) {
            val buf: ByteBuffer = codec.getInputBuffer(idx)!!
            buf.clear()
            buf.put(yuv)
            codec.queueInputBuffer(idx, 0, yuv.size, presentationUs, 0)
            presentationUs += 1_000_000L / fps
        }
        drain(endOfStream = false)
    }

    fun finish() {
        val idx = codec.dequeueInputBuffer(10_000)
        if (idx >= 0) {
            codec.queueInputBuffer(idx, 0, 0, presentationUs,
                MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        }
        drain(endOfStream = true)
        muxer.stop()
        muxer.release()
        codec.stop()
        codec.release()
    }

    // ── private ───────────────────────────────────────────────────────────────

    private fun drain(endOfStream: Boolean) {
        val timeout = if (endOfStream) 100_000L else 0L
        while (true) {
            val out = codec.dequeueOutputBuffer(bufferInfo, timeout)
            when {
                out == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    trackIndex = muxer.addTrack(codec.outputFormat)
                    muxer.start()
                    muxerStarted = true
                }
                out >= 0 -> {
                    val buf = codec.getOutputBuffer(out) ?: run {
                        codec.releaseOutputBuffer(out, false); return@when
                    }
                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                        bufferInfo.size = 0
                    }
                    if (bufferInfo.size > 0 && muxerStarted) {
                        buf.position(bufferInfo.offset)
                        buf.limit(bufferInfo.offset + bufferInfo.size)
                        muxer.writeSampleData(trackIndex, buf, bufferInfo)
                    }
                    codec.releaseOutputBuffer(out, false)
                    if (bufferInfo.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
                }
                out == MediaCodec.INFO_TRY_AGAIN_LATER -> {
                    if (!endOfStream) return
                }
                else -> Log.w("VideoEncoder", "Unexpected dequeue result: $out")
            }
        }
    }

    /** Convert ARGB_8888 Bitmap to NV21 (YUV 4:2:0 semi-planar) bytes. */
    private fun bitmapToNV21(bmp: Bitmap): ByteArray {
        val w = bmp.width
        val h = bmp.height
        val argb = IntArray(w * h)
        bmp.getPixels(argb, 0, w, 0, 0, w, h)

        val nv21 = ByteArray(w * h * 3 / 2)
        var yOff = 0
        var uvOff = w * h

        for (j in 0 until h) {
            for (i in 0 until w) {
                val p = argb[j * w + i]
                val r = (p shr 16) and 0xff
                val g = (p shr 8)  and 0xff
                val b =  p         and 0xff

                val y = (( 66 * r + 129 * g +  25 * b + 128) shr 8) + 16
                val u = ((-38 * r -  74 * g + 112 * b + 128) shr 8) + 128
                val v = ((112 * r -  94 * g -  18 * b + 128) shr 8) + 128

                nv21[yOff++] = y.coerceIn(0, 255).toByte()
                if (j % 2 == 0 && i % 2 == 0) {
                    // NV21: V first, then U
                    nv21[uvOff++] = v.coerceIn(0, 255).toByte()
                    nv21[uvOff++] = u.coerceIn(0, 255).toByte()
                }
            }
        }
        return nv21
    }
}
