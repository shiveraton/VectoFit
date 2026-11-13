from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from apps.assessments.services.video_processor import VideoProcessor


class VideoAspectRatioTests(SimpleTestCase):
    def frame(self, height, width, target_width=640, target_height=360):
        source = np.full((height, width, 3), 100, dtype=np.uint8)
        with patch(
            "apps.assessments.services.video_processor.apply_clahe",
            side_effect=lambda frame, **kwargs: frame,
        ):
            return VideoProcessor.process_frame(
                source,
                target_width=target_width,
                target_height=target_height,
            )

    def test_portrait_keeps_body_proportions_with_side_padding(self):
        result = self.frame(1440, 810)
        self.assertEqual(result.shape, (360, 640, 3))
        self.assertTrue(np.all(result[:, :219] == 0))
        self.assertTrue(np.all(result[:, 219:421] == 100))
        self.assertTrue(np.all(result[:, 421:] == 0))

    def test_matching_landscape_has_no_padding(self):
        self.assertTrue(np.all(self.frame(720, 1280) == 100))

    def test_square_is_centered_without_stretching(self):
        result = self.frame(500, 500)
        self.assertTrue(np.all(result[:, :140] == 0))
        self.assertTrue(np.all(result[:, 140:500] == 100))
        self.assertTrue(np.all(result[:, 500:] == 0))

    def test_odd_target_dimensions_are_preserved(self):
        result = self.frame(1440, 810, target_width=641, target_height=361)
        self.assertEqual(result.shape, (361, 641, 3))
