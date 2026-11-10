import csv
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from apps.annotator import tests as annotator_tests
from apps.datasets.models import KneeAnnotation
from .agreement import agreement_metrics
from .history import history_for
from .models import ValidationAnnotation, ValidationAnnotationEvent, ValidationSample


class ValidationWorkflowTests(APITestCase):
    def setUp(self):
        annotator_tests.AssignmentAccessTests.setUp(self)
        self.other.profile.is_validator = True
        self.other.profile.save(update_fields=["is_validator"])
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.other).key)
        self.selection = ValidationSample.objects.create(
            repetition=self.sample, position=0, protocol_version="v0.1",
        )
        self.url = f"/api/validation/annotations/{self.sample.pk}/"
        self.payload = {"left_knee": "aligned", "right_knee": "aligned", "notes": "Independent"}

    def export_agreement(self, output):
        call_command("export_validation_agreement", validator=self.other.username, output=output, stdout=StringIO())
        with output.open() as stream:
            return list(csv.DictReader(stream))

    def test_sample_is_fixed_and_blinded(self):
        first = self.client.get("/api/validation/sample/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual([row["repetition_id"] for row in first.data], [self.sample.pk])
        self.assertEqual(set(first.data[0]), {"repetition_id", "assessment_rep_id", "rep_number",
                                             "start_frame", "end_frame", "protocol_version", "video_url"})
        self.assertEqual(self.client.get("/validation/sample/").data[0]["repetition_id"], self.sample.pk)
        self.assertNotIn("good", str(first.data))
        self.assertNotIn("bad", str(first.data))

    def test_own_rating_is_derived_and_revisions_append_history(self):
        response = self.client.put(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["overall"], "good")
        self.assertEqual(response.data["protocol_version"], "v0.1")
        response = self.client.put(self.url, {**self.payload, "left_knee": "deviated",
                                             "right_knee": "unassessable"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["overall"], "bad")
        self.assertEqual(ValidationAnnotation.objects.count(), 1)
        self.assertEqual(ValidationAnnotationEvent.objects.count(), 2)
        self.assertFalse(KneeAnnotation.objects.exists())
        self.assertEqual([row["payload"]["overall"] for row in history_for(self.sample.pk, "validation")], ["good", "bad"])
        event = ValidationAnnotationEvent.objects.first()
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            ValidationAnnotationEvent.objects.all().update(source="annotation")
        with self.assertRaises(ValidationError):
            event.delete()
        with self.assertRaises(ValidationError):
            ValidationAnnotation.objects.all().update(left_knee="aligned")

    def test_validator_cannot_read_or_write_main_routes_even_with_staff_flag(self):
        for staff in (False, True):
            self.other.is_staff = staff
            self.other.save(update_fields=["is_staff"])
            for path in ("/api/annotator/datasets/", "/api/datasets/", "/api/training/jobs/"):
                self.assertEqual(self.client.get(path).status_code, 403)
            for path in (f"/api/datasets/dataset-samples/{self.sample.pk}/",
                         f"/api/annotator/samples/{self.sample.pk}/rating/", "/api/accounts/profile/current/"):
                self.assertEqual(self.client.patch(path, {"knee_annotation": None}, format="json").status_code, 403)
        self.assertFalse(KneeAnnotation.objects.exists())

    def test_account_response_exposes_effective_validator_role(self):
        response = self.client.get("/api/accounts/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_validator"])
        self.assertFalse(response.data["is_annotator"])

    def test_non_validator_denied_and_inputs_cannot_spoof_identity_or_overall(self):
        for value in ({"left_knee": "aligned"}, {**self.payload, "overall": "bad"},
                      {**self.payload, "validator": self.user.pk},
                      {**self.payload, "left_knee": "invalid"}):
            self.assertEqual(self.client.put(self.url, value, format="json").status_code, 400)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user).key)
        self.assertEqual(self.client.get("/api/validation/sample/").status_code, 403)
        self.assertEqual(self.client.put(self.url, self.payload, format="json").status_code, 403)

    def test_uniqueness_and_unsampled_repetitions(self):
        self.client.put(self.url, self.payload, format="json")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ValidationAnnotation.objects.create(repetition=self.sample, validator=self.other,
                                                 protocol_version="v0.1", **self.payload)
        self.assertEqual(self.client.put("/api/validation/annotations/999999/", self.payload, format="json").status_code, 404)

    def test_signed_media_uses_frozen_membership_and_live_role(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            Path(directory, "assignment.mp4").write_bytes(b"blinded-video")
            url = urlsplit(self.client.get("/api/validation/sample/").data[0]["video_url"])
            response = APIClient().get(url.path + "?" + url.query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"blinded-video")
            self.assertEqual(response["Content-Disposition"], 'inline; filename="validation.mp4"')
            response.close()
            self.other.profile.is_validator = False
            self.other.profile.save(update_fields=["is_validator"])
            self.assertEqual(APIClient().get(url.path + "?" + url.query).status_code, 404)

    def test_freeze_is_idempotent_and_rejects_replacement(self):
        output = StringIO()
        call_command("freeze_validation_sample", repetition_ids=[self.sample.pk], protocol_version="v0.1", stdout=output)
        with self.assertRaises(CommandError):
            call_command("freeze_validation_sample", repetition_ids=[self.sample.pk], protocol_version="v0.2", stdout=output)

    def test_export_reports_pairs_exclusions_and_undefined_kappa(self):
        self.client.put(self.url, self.payload, format="json")
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation={
            "left": {"grade": "aligned", "direction": "none"},
            "right": {"grade": "aligned", "direction": "none"},
            "symmetry_observation": "uncertain", "notes": "",
        })
        with TemporaryDirectory() as directory:
            output = Path(directory, "agreement.csv")
            rows = self.export_agreement(output)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["agreement_percent"], "100.0")
            self.assertEqual(rows[0]["kappa_status"], "constant_marginals")
            self.assertTrue(output.with_name("agreement_pairs.csv").exists())

    def test_export_reports_missing_and_disputed_consensus(self):
        self.client.put(self.url, self.payload, format="json")
        with TemporaryDirectory() as directory:
            output = Path(directory, "agreement.csv")
            rows = self.export_agreement(output)
            self.assertEqual(rows[0]["paired_count"], "0")
            self.assertEqual(rows[0]["exclusions"], "consensus_missing=1")
            for left in ("aligned", "deviated"):
                user = get_user_model().objects.create_user(username="reference-" + left)
                KneeAnnotation.objects.create(sample=self.sample, annotator=user, annotation={
                    "left": {"grade": left, "direction": "uncertain"},
                    "right": {"grade": "aligned", "direction": "none"},
                    "symmetry_observation": "uncertain", "notes": "",
                })
            rows = {row["scope"]: row for row in self.export_agreement(output)}
            self.assertEqual(rows["left_knee"]["exclusions"], "consensus_disputed=1")
            self.assertEqual(rows["overall"]["exclusions"], "consensus_disputed=1")
            self.assertEqual(rows["right_knee"]["paired_count"], "1")

    def test_kappa_known_result_and_no_pairs(self):
        result = agreement_metrics([("good", "good"), ("good", "bad"),
                                    ("bad", "good"), ("bad", "bad")])
        self.assertEqual(result["cohens_kappa"], 0)
        self.assertEqual(result["agreement_percent"], 50)
        self.assertEqual(agreement_metrics([])["kappa_status"], "no_pairs")
