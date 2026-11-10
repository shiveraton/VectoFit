from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from rest_framework.test import APITestCase

from apps.annotator import tests as annotator_tests
from apps.datasets.models import KneeAnnotation
from apps.datasets.serializers import DatasetSerializer
from apps.training.services.data_loader import prepare_knee_samples
from apps.training.services.run_training_job import _build_manifest
from .models import ValidationAnnotation


class ValidationIsolationTests(APITestCase):
    def setUp(self):
        annotator_tests.AssignmentAccessTests.setUp(self)
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation={
            "left": {"grade": "aligned", "direction": "none"},
            "right": {"grade": "aligned", "direction": "none"},
            "symmetry_observation": "uncertain", "notes": "",
        })
        rep = self.sample.rep_assessment
        rep.landmark_series = [{"left_knee": [1, 2]}] * 3
        rep.save(update_fields=["landmark_series"])

    def reject_validation_queries(self, execute, sql, params, many, context):
        self.assertNotIn(ValidationAnnotation._meta.db_table.lower(), sql.lower())
        return execute(sql, params, many, context)

    def training_evidence(self):
        with patch("apps.training.services.data_loader._extract_sample_features", return_value=({}, {}, "frame_timestamps")), \
             patch("apps.training.services.data_loader.to_feature_row", return_value=[1.0] * 6):
            prepared = prepare_knee_samples([self.dataset])
        self.assertEqual(prepared.sample_ids, [self.sample.pk])
        job = SimpleNamespace(pk=1, feature_schema_version="fppa_v2", algorithm="xgboost")
        result = {"train_idx": [], "test_idx": [], "hyperparameters": {},
                  "class_mapping": {}, "target_names": [], "metrics": {}}
        with patch("apps.training.services.run_training_job.timezone.now") as now:
            now.return_value.isoformat.return_value = "fixed"
            manifest = _build_manifest(job, [self.dataset], prepared, result,
                                       "frontal", "knee_alignment", .3, 42)
        return prepared.sample_ids, manifest["manifest_sha256"]

    def test_training_and_manifest_hash_ignore_validation_annotations(self):
        with connection.execute_wrapper(self.reject_validation_queries):
            before = self.training_evidence()
        ValidationAnnotation.objects.create(
            repetition=self.sample, validator=self.other,
            left_knee="deviated", right_knee="aligned", protocol_version="knee_validation_v1",
        )
        with connection.execute_wrapper(self.reject_validation_queries):
            self.assertEqual(self.training_evidence(), before)

    def test_dataset_serialization_ignores_validation_annotations(self):
        with connection.execute_wrapper(self.reject_validation_queries):
            before = DatasetSerializer(self.dataset).data
        ValidationAnnotation.objects.create(
            repetition=self.sample, validator=self.other,
            left_knee="aligned", right_knee="aligned", protocol_version="knee_validation_v1",
        )
        with connection.execute_wrapper(self.reject_validation_queries):
            self.assertEqual(DatasetSerializer(self.dataset).data, before)
