import csv
import hashlib
import json
import zipfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.management.commands.export_dataset_annotations import read_csv
from apps.datasets.models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
    Participant,
    ViewAngle,
)
from apps.datasets.services.bulk_import import _participant_from_path, inspect_archive
from apps.datasets.services.import_executor import _create_dataset_records
from apps.exercises.models import ExerciseVariant


class AnnotationExportTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "snapshot"
        self.manifest = self.root / "manifest.csv"
        self.user = get_user_model().objects.create_user(username="export-rater")
        self.other = get_user_model().objects.create_user(username="second-rater")
        self.dataset = Dataset.objects.create(
            name="Export", exercise_type="bodyweight_squat", purpose="training"
        )
        participant = Participant.objects.create(participant_code="MDY_P01")
        angle, _ = ViewAngle.objects.get_or_create(angle_variant="frontal")
        self.video = DatasetVideo.objects.create(
            dataset=self.dataset,
            participant=participant,
            view_angle=angle,
            video_file="stored-name.mp4",
            source_path="mdy_P01/frontal/mdy_P01_front_v1.mp4",
            status="READY",
        )
        variant = ExerciseVariant.objects.create(name="Export squat", variant_type="BW")
        self.session = AssessmentSession.objects.create(
            user=self.user, exercise_variant=variant
        )
        self.sample = self.make_sample(1, 10, 50)
        self.second_sample = self.make_sample(2, 60, 100)
        self.write_manifest()

    def make_sample(self, number, start, end):
        rep = RepAssessment.objects.create(
            session=self.session,
            rep_number=number,
            start_frame=start,
            end_frame=end,
            landmark_series=[],
        )
        return DatasetSample.objects.create(
            dataset=self.dataset, dataset_video=self.video, rep_assessment=rep
        )

    def write_manifest(self, rows=None):
        rows = (
            rows
            if rows is not None
            else [
                {
                    "video_id": "mdy_P01_front_v1",
                    "participant_id": "mdy_P01",
                    "source": "mendeley_bwsl_v1",
                    "view": "frontal",
                    "filename": "videos/mdy_P01_front_v1.mp4",
                }
            ]
        )
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=["video_id", "participant_id", "source", "view", "filename"],
            )
            writer.writeheader()
            writer.writerows(rows)

    def annotate(self, user=None, value="aligned", sample=None):
        annotation = (
            None
            if value is None
            else {
                "left": {"grade": value, "direction": "none"},
                "right": {"grade": "aligned", "direction": None},
                "symmetry_observation": "symmetric",
                "notes": 'Comma, newline\nand "quotes": café',
            }
        )
        return KneeAnnotation.objects.create(
            sample=sample or self.sample,
            annotator=user or self.user,
            annotation=annotation,
        )

    def export(self, **options):
        call_command(
            "export_dataset_annotations",
            "--annotator",
            f"{self.user.pk}=annotator_01",
            "--annotator",
            f"{self.other.pk}=annotator_02",
            dataset_id=self.dataset.pk,
            manifest=self.manifest,
            output=self.output,
            stdout=StringIO(),
            **options,
        )

    def rows(self, name):
        with (self.output / name).open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def test_exports_multiple_repetitions_current_ratings_and_hashes(self):
        first = self.annotate()
        latest = self.annotate(value="deviated")
        KneeAnnotation.objects.filter(pk__in=[first.pk, latest.pk]).update(
            created_at=timezone.now()
        )
        self.annotate(user=self.other)
        self.export(history=True)
        reps = self.rows("repetitions.csv")
        self.assertEqual([int(row["rep_number"]) for row in reps], [1, 2])
        self.assertEqual(reps[0]["participant_id"], "mdy_P01")
        self.assertEqual(reps[0]["start_frame"], "10")
        rows = self.rows("annotator_01.csv")
        self.assertEqual(rows[0]["record_id"], str(latest.pk))
        self.assertEqual(rows[0]["target"], "bad")
        self.assertEqual(rows[0]["notes"], latest.annotation["notes"])
        self.assertIsNone(json.loads(rows[0]["annotation_json"])["right"]["direction"])
        self.assertEqual(rows[1]["rating_status"], "missing")
        self.assertEqual(self.rows("annotator_02.csv")[0]["target"], "good")
        self.assertEqual(len(self.rows("history.csv")), 3)
        metadata = json.loads((self.output / "snapshot.json").read_text())
        self.assertEqual(metadata["repetition_count"], 2)
        self.assertEqual(
            metadata["manifest_sha256"],
            hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
        )
        for name, expected in metadata["sha256"].items():
            self.assertEqual(
                hashlib.sha256((self.output / name).read_bytes()).hexdigest(), expected
            )
        self.assertNotIn(
            self.user.username, (self.output / "snapshot.json").read_text()
        )
        self.assertEqual(KneeAnnotation.objects.count(), 3)

    def test_clear_does_not_resurrect_older_rating(self):
        self.annotate()
        cleared = self.annotate(value=None)
        self.export()
        row = self.rows("annotator_01.csv")[0]
        self.assertEqual(row["record_id"], str(cleared.pk))
        self.assertEqual(row["rating_status"], "cleared")
        self.assertEqual(row["annotation_json"], "null")
        self.assertEqual(row["target"], "")
        self.assertFalse((self.output / "history.csv").exists())

    def test_rejects_ambiguous_matching_without_publishing(self):
        DatasetVideo.objects.create(
            dataset=self.dataset,
            participant=self.video.participant,
            view_angle=self.video.view_angle,
            video_file="duplicate.mp4",
            source_path="elsewhere/mdy_P01_front_v1.mp4",
            status="READY",
        )
        with self.assertRaisesMessage(CommandError, "expected one database video"):
            self.export()
        self.assertFalse(self.output.exists())

    def test_explicit_mapping_handles_renamed_source_path(self):
        self.video.source_path = "original-recording.mp4"
        self.video.save()
        mapping = self.root / "video-map.csv"
        mapping.write_text(
            f"video_id,dataset_video_id\nmdy_P01_front_v1,{self.video.pk}\n"
        )
        self.export(video_map=mapping)
        self.assertEqual(
            self.rows("repetitions.csv")[0]["dataset_video_id"], str(self.video.pk)
        )

    def test_rejects_incorrect_participant_group(self):
        self.video.participant.participant_code = "MDY_P01_V1"
        self.video.participant.save()
        with self.assertRaisesMessage(CommandError, "participant does not match"):
            self.export()
        self.assertFalse(self.output.exists())

    def test_rejects_missing_or_invalid_boundaries(self):
        for start, end in ((None, 50), (50, 50), (51, 50)):
            with self.subTest(start=start, end=end):
                RepAssessment.objects.filter(pk=self.sample.rep_assessment_id).update(
                    start_frame=start, end_frame=end
                )
                with self.assertRaisesMessage(CommandError, "frame boundaries"):
                    self.export()
                self.assertFalse(self.output.exists())

    def test_rejects_video_without_segmented_samples(self):
        self.dataset.samples.all().delete()
        with self.assertRaisesMessage(CommandError, "segmented sample"):
            self.export()

    def test_rejects_duplicate_manifest_ids(self):
        with self.manifest.open() as stream:
            row = next(csv.DictReader(stream))
        self.write_manifest([row, row])
        with self.assertRaisesMessage(CommandError, "nonempty and unique"):
            self.export()

    def test_refuses_overwrite(self):
        self.export()
        previous = (self.output / "snapshot.json").read_bytes()
        with self.assertRaisesMessage(CommandError, "Output already exists"):
            self.export()
        self.assertEqual((self.output / "snapshot.json").read_bytes(), previous)

    def test_other_dataset_ratings_are_not_exported(self):
        other_dataset = Dataset.objects.create(
            name="Other", exercise_type="bodyweight_squat", purpose="training"
        )
        other_sample = DatasetSample.objects.create(
            dataset=other_dataset,
            rep_assessment=self.sample.rep_assessment,
        )
        self.annotate(sample=other_sample)
        self.export(history=True)
        self.assertEqual(self.rows("history.csv"), [])
        self.assertTrue(
            all(
                row["rating_status"] == "missing"
                for row in self.rows("annotator_01.csv")
            )
        )

    def test_write_failure_does_not_publish_partial_snapshot(self):
        with (
            patch(
                "apps.datasets.management.commands.export_dataset_annotations.write_csv",
                side_effect=OSError("disk full"),
            ),
            self.assertRaisesMessage(CommandError, "disk full"),
        ):
            self.export()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".annotation-export-*")))

    def test_future_record_is_not_included_at_export_cutoff(self):
        previous = self.annotate()
        future = self.annotate(value="deviated")
        KneeAnnotation.objects.filter(pk=future.pk).update(
            created_at=timezone.now() + timedelta(days=1)
        )
        self.export(history=True)
        self.assertEqual(
            self.rows("annotator_01.csv")[0]["record_id"], str(previous.pk)
        )
        self.assertEqual(len(self.rows("history.csv")), 1)

    def test_unlabelled_import_always_requires_manual_review(self):
        for policy in ("source", "all", "subset"):
            with self.subTest(policy=policy):
                videos = [
                    {
                        "archive_path": "mdy_P01_front_v1.mp4",
                        "participant_code": "MDY_P01",
                        "angle_variant": "frontal",
                        "source_label": None,
                    },
                    {
                        "archive_path": "mdy_P01_front_v2.mp4",
                        "participant_code": "MDY_P01",
                        "angle_variant": "frontal",
                        "source_label": True,
                    },
                ]
                dataset, _ = _create_dataset_records(
                    validated_data={
                        "name": "Unlabelled import",
                        "exercise_type": "bodyweight_squat",
                        "purpose": "training",
                        "review_policy": policy,
                    },
                    videos=videos,
                    stored_by_archive_path={
                        video["archive_path"]: video["archive_path"] for video in videos
                    },
                )
                unlabelled = dataset.videos.get(source_label__isnull=True)
                self.assertTrue(unlabelled.requires_manual_review)
                labelled = dataset.videos.get(source_label=True)
                self.assertEqual(labelled.requires_manual_review, policy == "all")
                self.assertEqual(unlabelled.participant_id, labelled.participant_id)


class SourceParticipantImportTests(SimpleTestCase):
    def test_flat_variants_share_source_prefixed_participant(self):
        for name in ("mdy_P01_front_v1.mp4", "mdy_P01_front_v2.mp4"):
            self.assertEqual(_participant_from_path([name]), "MDY_P01")
        self.assertEqual(_participant_from_path(["zen_P01_front.mp4"]), "ZEN_P01")

    def test_source_prefixed_directory_groups_original_filenames(self):
        self.assertEqual(
            _participant_from_path(["mdy_P01", "frontal", "original1.mp4"]), "MDY_P01"
        )
        self.assertEqual(
            _participant_from_path(["mdy_P01", "frontal", "original2.mp4"]), "MDY_P01"
        )

    def test_existing_numeric_directory_grouping_is_preserved(self):
        self.assertEqual(
            _participant_from_path(["P01", "frontal", "anything.mp4"]), "P01"
        )
        self.assertEqual(_participant_from_path(["subject_2", "good.mp4"]), "P02")

    def test_archive_preview_counts_variants_as_one_participant(self):
        with TemporaryDirectory() as directory:
            archive_path = Path(directory) / "dataset.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in (
                    "mdy_P01_front_v1.mp4",
                    "mdy_P01_front_v2.mp4",
                    "zen_P01_front.mp4",
                ):
                    archive.writestr(name, b"video")
            manifest = inspect_archive(archive_path)
        self.assertEqual(manifest["errors"], [])
        self.assertEqual(manifest["participant_count"], 2)
        self.assertEqual(manifest["file_count"], 3)

    def test_conflicting_source_labels_are_still_rejected(self):
        with TemporaryDirectory() as directory:
            archive_path = Path(directory) / "dataset.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("good/bad/mdy_P01_front.mp4", b"video")
            manifest = inspect_archive(archive_path)
        self.assertTrue(
            any("conflicting good/bad" in error for error in manifest["errors"])
        )
        self.assertEqual(manifest["file_count"], 0)

    def test_label_prefixes_do_not_split_participants(self):
        for name in ("good_P01_front.mp4", "bad_P01_front.mp4", "front_P01_good.mp4"):
            with self.subTest(name=name):
                self.assertEqual(_participant_from_path([name]), "P01")

    def test_unrelated_numbered_folder_does_not_override_participant(self):
        self.assertEqual(
            _participant_from_path(["recording_01", "frontal", "P02.mp4"]), "P02"
        )


class AnnotationCSVHeaderTests(SimpleTestCase):
    def test_duplicate_manifest_columns_are_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text("video_id,video_id,participant_id\nfirst,second,P01\n")
            with self.assertRaisesMessage(CommandError, "duplicate columns: video_id"):
                read_csv(path, {"video_id", "participant_id"})

    def test_duplicate_mapping_columns_are_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.csv"
            path.write_text("video_id,dataset_video_id,dataset_video_id\nvideo,1,2\n")
            with self.assertRaisesMessage(
                CommandError, "duplicate columns: dataset_video_id"
            ):
                read_csv(path, {"video_id", "dataset_video_id"})
