import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core import signing
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase, APIRequestFactory

from apps.annotator import tests as access_tests
from .media_views import MEDIA_SIGNING_SALT
from .services.media import protected_file_response


class ProtectedPlaybackTests(APITestCase):
    def setUp(self):
        access_tests.AssignmentAccessTests.setUp(self)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.media_root = directory.name
        setting = override_settings(MEDIA_ROOT=self.media_root)
        setting.enable()
        self.addCleanup(setting.disable)
        self.body = b"0123456789abcdef"
        Path(self.media_root, "assignment.mp4").write_bytes(self.body)
        self.url = f"/api/annotator/videos/{self.video.pk}/"
        token = signing.dumps({"kind": "dataset-video", "object_id": self.video.pk, "user_id": self.user.pk}, salt=MEDIA_SIGNING_SALT)
        self.signed_url = f"/api/datasets/media/dataset-video/{self.video.pk}/?token={token}"

    def read(self, response):
        try:
            return b"".join(response.streaming_content) if response.streaming else response.content
        finally:
            response.close()

    def test_full_file_and_neutral_filename_without_nginx(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], str(len(self.body)))
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(response["Content-Disposition"], 'inline; filename="review-video.mp4"')
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertEqual(self.read(response), self.body)

    def test_closed_open_suffix_and_clamped_ranges_for_both_endpoints(self):
        for url in (self.url, self.signed_url):
            for header, expected, span in (
                ("bytes=2-5", b"2345", "2-5"),
                ("bytes=10-", b"abcdef", "10-15"),
                ("bytes=-4", b"cdef", "12-15"),
                ("bytes=12-100", b"cdef", "12-15"),
                ("bytes=-100", self.body, "0-15"),
                ("bytes=0-0", b"0", "0-0"),
            ):
                with self.subTest(url=url, header=header):
                    response = self.client.get(url, HTTP_RANGE=header)
                    self.assertEqual(response.status_code, 206)
                    self.assertEqual(response["Content-Range"], f"bytes {span}/16")
                    self.assertEqual(response["Content-Length"], str(len(expected)))
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertEqual(self.read(response), expected)

    def test_invalid_ranges_return_416_without_file_bytes(self):
        for header in ("bytes=16-", "bytes=9-2", "bytes=-0", "bytes=-", "bytes=0-1,4-5", "bytes=abc", "bytes=" + "9" * 100 + "-"):
            with self.subTest(header=header):
                response = self.client.get(self.url, HTTP_RANGE=header)
                self.assertEqual(response.status_code, 416)
                self.assertEqual(response["Content-Range"], "bytes */16")
                self.assertIn("no-store", response["Cache-Control"])
                self.assertEqual(self.read(response), b"")

    def test_empty_file_and_head(self):
        response = self.client.head(self.url, HTTP_RANGE="bytes=0-2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "16")
        self.assertEqual(self.read(response), b"")
        Path(self.media_root, "assignment.mp4").write_bytes(b"")
        response = self.client.get(self.url, HTTP_RANGE="bytes=0-")
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response["Content-Range"], "bytes */0")
        self.assertEqual(self.read(response), b"")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.read(response), b"")

    def test_if_range_without_validator_sends_full_representation(self):
        response = self.client.get(self.url, HTTP_RANGE="bytes=0-2", HTTP_IF_RANGE='"old-validator"')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.read(response), self.body)

    def test_revocation_blocks_new_range_requests_and_existing_signed_url(self):
        self.assertEqual(self.read(self.client.get(self.url, HTTP_RANGE="bytes=0-2")), b"012")
        self.assignment.is_active = False
        self.assignment.save()
        for url in (self.url, self.signed_url):
            response = self.client.get(url, HTTP_RANGE="bytes=4-8")
            self.assertEqual(response.status_code, 404)
            self.assertIn("no-store", response["Cache-Control"])

    def test_missing_and_unreadable_files_return_404(self):
        Path(self.media_root, "assignment.mp4").unlink()
        for url in (self.url, self.signed_url):
            self.assertEqual(self.client.get(url).status_code, 404)
        with patch("django.core.files.storage.FileSystemStorage._open", side_effect=PermissionError):
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_local_path_escape_is_denied(self):
        with TemporaryDirectory() as outside:
            path = Path(outside, "outside.mp4")
            path.write_bytes(b"private")
            self.video.video_file.name = str(path)
            self.video.save()
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_real_session_cookie_authorizes_public_playback(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.user)
        response = self.client.get(self.url, HTTP_RANGE="bytes=0-2")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(self.read(response), b"012")
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_wrong_role_and_review_ineligible_video_denied(self):
        self.user.profile.is_annotator = False
        self.user.profile.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.user.profile.is_annotator = True
        self.user.profile.save()
        self.video.requires_manual_review = False
        self.video.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_invalid_signed_token_is_private_404(self):
        response = self.client.get(f"/api/datasets/media/dataset-video/{self.video.pk}/?token=invalid")
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response["Cache-Control"])


class MediaResourceTests(SimpleTestCase):
    def test_range_response_closes_even_if_stream_never_started(self):
        file = io.BytesIO(b"0123456789")
        media = Mock(name="media")
        type(media).path = property(lambda _: (_ for _ in ()).throw(NotImplementedError()))
        media.name = "video.mp4"
        media.size = 10
        media.open.return_value = file
        request = APIRequestFactory().get("/", HTTP_RANGE="bytes=0-2")
        response = protected_file_response(request, media)
        self.assertFalse(file.closed)
        response.close()
        self.assertTrue(file.closed)
