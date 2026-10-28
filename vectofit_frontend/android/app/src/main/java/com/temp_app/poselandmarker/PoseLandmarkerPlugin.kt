package com.margelo.nitro.vectofit

import android.util.Log

import com.google.mediapipe.framework.image.MediaImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker
import com.margelo.nitro.NitroModules
import com.margelo.nitro.camera.HybridFrameSpec
import com.margelo.nitro.camera.public.NativeFrame

class HybridPoseLandmarkerPlugin : HybridPoseLandmarkerPluginSpec() {

    private val poseLandmarker: PoseLandmarker

    init {
        val context = NitroModules.applicationContext
            ?: throw IllegalStateException(
                "VectoFit Pose Landmarker requires a ReactApplicationContext."
            )

        val baseOptions = BaseOptions.builder()
            .setModelAssetPath("pose_landmarker_full.task")
            .build()

        val options = PoseLandmarker.PoseLandmarkerOptions.builder()
            .setBaseOptions(baseOptions)
            .setRunningMode(RunningMode.IMAGE)
            .build()

        poseLandmarker = PoseLandmarker.createFromOptions(
            context,
            options
        )

        Log.d(
            "VectoFitPose",
            "Pose Landmarker initialized successfully"
        )
    }

    override fun detect(frame: HybridFrameSpec): DoubleArray {
        val nativeFrame = frame as? NativeFrame ?: return DoubleArray(0)

        val imageProxy = nativeFrame.image
        val mediaImage = imageProxy.image ?: return DoubleArray(0)

        Log.d(
            "VectoFitPose",
            "Input image: ${mediaImage.width}x${mediaImage.height}, " +
                "format=${imageProxy.format}, " +
                "rotation=${imageProxy.imageInfo.rotationDegrees}"
        )

        val mpImage = MediaImageBuilder(mediaImage).build()

        val result = poseLandmarker.detect(mpImage)
        val detectedPoses = result.landmarks()

        Log.d(
            "VectoFitPose",
            "MediaPipe detected ${detectedPoses.size} pose(s)"
        )

        val poseLandmarks = detectedPoses.firstOrNull()
            ?: return DoubleArray(0)


        if (poseLandmarks.size < 33) {
            return DoubleArray(0)
        }

        val flattened = DoubleArray(33 * 4)

        for (i in 0 until 33) {
            val landmark = poseLandmarks[i]

            flattened[i * 4] = landmark.x().toDouble()
            flattened[i * 4 + 1] = landmark.y().toDouble()
            flattened[i * 4 + 2] = landmark.z().toDouble()
            flattened[i * 4 + 3] = landmark.visibility().orElse(0f).toDouble()
        }

        return flattened
    }
}