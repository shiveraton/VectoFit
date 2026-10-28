We'll implement this as a real dataset-ingestion pipeline for VectoFit, keeping the existing single-video workflow available while adding bulk import.

The main architectural change is that one Dataset will contain many DatasetVideo records, each with its own participant, camera angle, source label, file, and processing status. The processing worker will continue producing repetition-level assessments and samples, which the existing training pipeline can use.

## 1. The import format

For the first implementation, standardize your ZIP archive like this:

```
VectoFit_Bodyweight_Squat_v1.zip
├── good/
│   ├── diagonal/
│   │   ├── P01.mp4
│   │   ├── P02.mp4
│   │   └── ...
│   ├── frontal/
│   │   ├── P01.mp4
│   │   └── ...
│   └── sagittal/
│       ├── P01.mp4
│       └── ...
└── bad/
    ├── diagonal/
    │   ├── P01.mp4
    │   └── ...
    ├── frontal/
    │   └── ...
    └── sagittal/
        └── ...
```

Use anonymized participant codes such as `P01` through `P26`. The importer will read the folder structure, so you won't need to enter participant IDs, camera angles, or good/bad labels individually.

The importer will preview the archive before committing anything. Missing combinations can be reported as warnings rather than assumed to be errors, since your three camera views may not all have identical coverage.

One scientific safeguard: this implementation propagates a video's good/bad folder label to each repetition extracted from that video. That is appropriate only when the entire clip consistently represents that label. Mixed-quality clips should be imported without an inherited label and annotated at the repetition level instead.

## 2. Backend: add `DatasetVideo`

File: `vectofit_backend/apps/datasets/models.py`

Keep the existing `Dataset` model and its old fields for compatibility. Add the new model below `Dataset` and before `DatasetSample`.

First, add these imports if they are not already present:

```
import uuidfrom pathlib import PurePosixPath
```

Add:

```
def dataset_video_upload_to(instance, filename):    safe_name = PurePosixPath(filename.replace("\\", "/")).name    return (        f"dataset_videos/dataset_{instance.dataset_id}/"        f"{uuid.uuid4().hex}_{safe_name}"    )class DatasetVideo(models.Model):    class Status(models.TextChoices):        PENDING = "PENDING", "Pending"        PROCESSING = "PROCESSING", "Processing"        READY = "READY", "Ready"        FAILED = "FAILED", "Failed"    dataset = models.ForeignKey(        Dataset,        on_delete=models.CASCADE,        related_name="videos",    )    participant = models.ForeignKey(        Participant,        on_delete=models.PROTECT,        related_name="dataset_videos",    )    view_angle = models.ForeignKey(        ViewAngle,        on_delete=models.RESTRICT,        related_name="dataset_videos",    )    video_file = models.FileField(        upload_to=dataset_video_upload_to,    )
```

Now add the relationship to your existing `DatasetSample` model:

```
dataset_video = models.ForeignKey(    "DatasetVideo",    on_delete=models.SET_NULL,    null=True,    blank=True,    related_name="samples",)
```

Do not remove its existing `dataset` or `rep_assessment` fields. Legacy samples can leave `dataset_video` empty.

Run these commands from your backend directory:

```
python manage.py makemigrations datasets
python manage.py migrate
```

This generates the migration from your actual local models rather than requiring you to hand-write a migration against the wrong database state.

## 3. Backend: build a ZIP manifest parser

New file: `vectofit_backend/apps/datasets/services/bulk_import.py`

This is responsible for inspecting the archive without extracting arbitrary paths onto your server. It identifies participant codes, view angles, and good/bad labels from the folder and filename tokens.

```
import reimport zipfilefrom collections import Counterfrom pathlib import Path, PurePosixPathfrom django.conf import settingsVIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi"}GOOD_TOKENS = {"good", "correct", "proper", "pass", "acceptable"}BAD_TOKENS = {"bad", "incorrect", "poor", "fail", "faulty"}LABEL_TOKENS = GOOD_TOKENS | BAD_TOKENSANGLE_TOKENS = {    "diagonal",    "frontal",    "front",    "sagittal",    "side",    "45",    "deg",    "degree",    "degrees",}METADATA_TOKENS = (    LABEL_TOKENS    | ANGLE_TOKENS    | {        "squat",        "bodyweight",        "bw",        "form",        "view",
```

A file with no class label, conflicting labels, conflicting angles, or no recognizable participant will block the import. Other non-video files are ignored.

## 4. Backend: preview and commit endpoints

File: `vectofit_backend/apps/datasets/serializers.py`

Make the parent dataset's angle optional, because a collection contains videos from multiple angles:

```
view_angle = serializers.PrimaryKeyRelatedField(    queryset=ViewAngle.objects.all(),    allow_null=True,    required=False,)
```

In the existing `DatasetSerializer`, add a field for the number of child videos:

```
video_count = serializers.SerializerMethodField()ready_video_count = serializers.SerializerMethodField()failed_video_count = serializers.SerializerMethodField()
```

Add these methods:

```
def get_video_count(self, obj):    return obj.videos.count()def get_ready_video_count(self, obj):    return obj.videos.filter(        status="READY"    ).count()def get_failed_video_count(self, obj):    return obj.videos.filter(        status="FAILED"    ).count()
```

Add `video_count`, `ready_video_count`, and `failed_video_count` to the serializer's `Meta.fields` list.

Also add `dataset_video` to the existing `DatasetSampleSerializer.Meta.fields`. Declare it read-only:

```
dataset_video = serializers.PrimaryKeyRelatedField(    read_only=True)
```

Then add a serializer for inspecting individual imported videos:

```
class DatasetVideoSerializer(serializers.ModelSerializer):    participant_code = serializers.CharField(        source="participant.participant_code",        read_only=True,    )    view_angle_name = serializers.CharField(        source="view_angle.angle_variant",        read_only=True,    )    video_url = serializers.SerializerMethodField()    class Meta:        model = DatasetVideo        fields = [            "id",            "dataset",            "participant",            "participant_code",            "view_angle",            "view_angle_name",            "video_file",            "video_url",            "source_label",            "source_path",            "status",            "error_message",            "created_at",            "updated_at",        ]        read_only_fields = fields    def get_video_url(self, obj):        if not obj.video_file:            return None
```

Ensure `DatasetVideo` is imported at the top of the serializer file.

### Add the import endpoints

File: `vectofit_backend/apps/datasets/views.py`

Add these imports:

```
import uuidimport zipfilefrom pathlib import Path, PurePosixPathfrom django.conf import settingsfrom django.core.files import Filefrom django.core.files.storage import default_storagefrom django.db import transactionfrom rest_framework import permissions, status, viewsetsfrom rest_framework.parsers import (    JSONParser,    MultiPartParser,    FormParser,)from rest_framework.response import Responsefrom rest_framework.views import APIViewfrom .models import (    Dataset,    DatasetSample,    DatasetVideo,    Participant,    ViewAngle,)from .serializers import (    DatasetSerializer,    DatasetSampleSerializer,    DatasetVideoSerializer,    ParticipantSerializer,    ViewAngleSerializer,)from .services.bulk_import import (    empty_manifest,
```

Keep your existing views and append the following two API views. The existing single-video endpoint can remain in place.

```
class DatasetImportPreviewView(APIView):    permission_classes = [permissions.IsAdminUser]    parser_classes = [MultiPartParser, FormParser]    def post(self, request):        uploaded_file = request.FILES.get("zip_file")        if not uploaded_file:            result = empty_manifest()            result["errors"].append(                "Select a ZIP archive to upload."            )            result["upload_token"] = None            return Response(result)        max_bytes = getattr(            settings,            "DATASET_IMPORT_MAX_BYTES",            4 * 1024**3,        )        if uploaded_file.size > max_bytes:            result = empty_manifest()            result["errors"].append(                "The ZIP archive exceeds the configured upload-size limit."            )            result["upload_token"] = None            return Response(result)        if not uploaded_file.name.lower().endswith(".zip"):            result = empty_manifest()            result["errors"].append(                "Only ZIP archives are supported."            )            result["upload_token"] = None            return Response(result)
```

The two endpoints are:

```
POST /api/datasets/import/preview/
POST /api/datasets/import/
```

The preview request uses multipart form data with a `zip_file` field. The commit request sends JSON metadata and the returned `upload_token`.

### Expose imported videos in the API

Add this viewset to `views.py`:

```
class DatasetVideoViewSet(viewsets.ReadOnlyModelViewSet):    queryset = DatasetVideo.objects.select_related(        "dataset",        "participant",        "view_angle",    ).all()    serializer_class = DatasetVideoSerializer    permission_classes = [permissions.IsAdminUser]    def get_queryset(self):        queryset = super().get_queryset()        dataset_id = self.request.query_params.get("dataset")        if dataset_id:            queryset = queryset.filter(dataset_id=dataset_id)        return queryset
```

File: `vectofit_backend/apps/datasets/urls.py`

Add the new view imports and register the video viewset. Add the two import paths before `include(router.urls)`:

```
from django.urls import include, pathfrom rest_framework.routers import DefaultRouterfrom .views import (    DatasetSampleViewSet,    DatasetViewSet,    DatasetVideoViewSet,    DatasetImportPreviewView,    DatasetBulkImportView,    ParticipantViewSet,    ViewAngleViewSet,)router = DefaultRouter()router.register(r"", DatasetViewSet, basename="dataset")router.register(    r"dataset-samples",    DatasetSampleViewSet,    basename="dataset-sample",)router.register(    r"dataset-videos",    DatasetVideoViewSet,    basename="dataset-video",)router.register(r"participant", ParticipantViewSet, basename="participant")router.register(r"view-angle", ViewAngleViewSet, basename="view-angle")urlpatterns = [    path(        "import/preview/",        DatasetImportPreviewView.as_view(),        name="dataset-import-preview",    ),    path(        "import/",
```

## 5. Backend: process each imported video

Your existing processing task is designed around a single `Dataset.video_file`. We will add a separate child-video task rather than change how old datasets are processed.

File: `vectofit_backend/apps/datasets/services/tasks.py`

Add `DatasetVideo` to the existing model imports:

```
from ..models import Dataset, DatasetSample, DatasetVideo
```

Append these functions to the file:

```
def refresh_dataset_collection_status(dataset_id):    statuses = list(        DatasetVideo.objects.filter(            dataset_id=dataset_id        ).values_list("status", flat=True)    )    if not statuses:        return    pending = {        DatasetVideo.Status.PENDING,        DatasetVideo.Status.PROCESSING,    }    if any(item in pending for item in statuses):        aggregate_status = "PROCESSING"    elif all(        item == DatasetVideo.Status.READY        for item in statuses    ):        aggregate_status = "READY"    elif all(        item == DatasetVideo.Status.FAILED        for item in statuses    ):        aggregate_status = "FAILED"    else:        aggregate_status = "PARTIAL"    failed_count = statuses.count(DatasetVideo.Status.FAILED)    dataset = Dataset.objects.get(pk=dataset_id)    dataset.status = aggregate_status    dataset.error_message = (        f"{failed_count} video(s) failed processing."
```

This reuses the existing `VideoProcessor`, `segment_reps`, `AssessmentSession`, and `RepAssessment` pipeline. It creates a `DatasetSample` for each extracted repetition and links that sample to both the parent dataset and the specific video.

The existing `process_dataset_video_task` stays unchanged.

## 6. Backend: make the training loader participant-aware

This is an essential part of the refactor. A parent collection has no single participant, so the training loader needs to get the participant from each sample's child video. Otherwise, it will reject the new collection because `dataset.participant_id` is empty.

File: `vectofit_backend/apps/training/services/data_loader.py`

In `_load_labelled_samples`, add `dataset_video__participant` to `select_related`:

```
samples = (    DatasetSample.objects.select_related(        "dataset_video__participant",        "rep_assessment__session",        "rep_assessment__session__body_profile",    )    .filter(        dataset=dataset,        is_correct__isnull=False,    )    .order_by("id"))
```

Then replace the loop in `build_samples()` with this version. It preserves the existing feature extraction and label conversion, but assigns groups per actual participant:

```
def build_samples(datasets, selected_features):    rows = []    labels = []    groups = []    warnings = []    errors = []    for dataset in datasets:        found_any = False        for sample, frames, session in _load_labelled_samples(dataset):            if sample.dataset_video_id:                participant_id = (                    sample.dataset_video.participant_id                )            else:                # Backward compatibility for old single-video datasets.                participant_id = dataset.participant_id            if participant_id is None:                errors.append(                    f"Dataset {dataset.pk} sample {sample.pk} "                    "has no participant assigned."                )                continue            found_any = True            try:                features = extract_rep_features(                    frames,                    fps=30.0,                    scale_factor=_scale_factor_for_session(session),                )                row = to_feature_row(
```

This allows you to select one dataset collection for training while the loader reads repetitions across all its child videos. The participant grouping keeps all of a participant's views and good/bad recordings on the same side of the train/test split.

## 7. Frontend: add the bulk-import service

File: `vectofit_admin/src/services/datasetService.ts`

Keep the existing methods and add these types and methods.

```
export interface DatasetImportFile {
  archive_path: string;
  filename: string;
  participant_code: string;
  view_angle: ViewAngle;
  source_label: boolean;
  size_bytes: number;
}

export interface DatasetImportPreview {
  upload_token: string | null;
  file_count: number;
  participant_count: number;
  by_angle: Record<ViewAngle, number>;
  by_label: {
    good: number;
    bad: number;
  };
  files: DatasetImportFile[];
  warnings: string[];
  errors: string[];
  ignored_file_count: number;
}

export interface DatasetBulkImportPayload {
  upload_token: string;
  name: string;
  description: string;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target: string;
}

export interface DatasetBulkImportResult {
  dataset: Dataset;
  imported_videos: number;
  queued_videos: number;
  queue_failures: Array<{
    video_id: number;
    error: string;
  }>;
}
```

Add the following inside `datasetService`:

```
async previewDatasetArchive(
  file: File,
): Promise<DatasetImportPreview> {
  const formData = new FormData();
  formData.append("zip_file", file);

  const response = await client.post<DatasetImportPreview>(
    "/datasets/import/preview/",
    formData,
  );

  return response.data;
},

async commitDatasetArchive(
  payload: DatasetBulkImportPayload,
): Promise<DatasetBulkImportResult> {
  const response = await client.post<DatasetBulkImportResult>(
    "/datasets/import/",
    payload,
  );

  return response.data;
},
```

If you want to show video counts on the Datasets page, also extend the existing `Dataset` interface:

```
video_count?: number;
ready_video_count?: number;
failed_video_count?: number;
```

And expand its status type:

```
export type DatasetStatus =
  | "PENDING"
  | "PROCESSING"
  | "READY"
  | "FAILED"
  | "PARTIAL";
```

## 8. Frontend: create the import modal

New file: `vectofit_admin/src/components/datasets/DatasetImportModal.vue`

The modal below implements the two-stage interaction: select ZIP → inspect manifest → confirm import. It keeps all discovered video metadata visible for review before submission.

```Vue
<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
  datasetService,
  type DatasetImportPreview,
} from "../../services/datasetService";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "imported", datasetName: string, videoCount: number): void;
}>();

const zipFile = ref<File | null>(null);
const preview = ref<DatasetImportPreview | null>(null);

const name = ref("VectoFit Bodyweight Squat v1");
const description = ref(
  "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.",
);
const exerciseType = ref("bodyweight_squat");
const purpose = ref("training");
const primaryTarget = ref("squat_quality");
const secondaryTarget = ref("biomechanical_errors");

const isPreviewing = ref(false);
const isImporting = ref(false);
const errorMessage = ref("");

const canImport = computed(() => {
  return (
    Boolean(preview.value?.upload_token) &&
    preview.value?.errors.length === 0 &&
    name.value.trim().length > 0 &&
    !isImporting.value
  );
});

const reset = () => {
  zipFile.value = null;
  preview.value = null;
  errorMessage.value = "";
  isPreviewing.value = false;
  isImporting.value = false;

  name.value = "VectoFit Bodyweight Squat v1";
  description.value =
    "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.";
  exerciseType.value = "bodyweight_squat";
  purpose.value = "training";
  primaryTarget.value = "squat_quality";
  secondaryTarget.value = "biomechanical_errors";
};

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) reset();
  },
);

const close = () => {
  if (isPreviewing.value || isImporting.value) return;
  emit("close");
};

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  preview.value = null;
  errorMessage.value = "";

  if (!file) {
    zipFile.value = null;
    return;
  }

  if (!file.name.toLowerCase().endsWith(".zip")) {
    zipFile.value = null;
    errorMessage.value = "Please select a ZIP archive.";
    input.value = "";
    return;
  }

  zipFile.value = file;
};

const previewArchive = async () => {
  if (!zipFile.value) {
    errorMessage.value = "Select a ZIP archive first.";
    return;
  }

  isPreviewing.value = true;
  preview.value = null;
  errorMessage.value = "";

  try {
    preview.value = await datasetService.previewDatasetArchive(
      zipFile.value,
    );

    if (preview.value.errors.length > 0) {
      errorMessage.value =
        "The archive has validation errors. Correct the structure and upload it again.";
    }
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.message ||
      "Could not preview the archive.";
  } finally {
    isPreviewing.value = false;
  }
};

const commitImport = async () => {
  if (!preview.value?.upload_token || !canImport.value) return;

  isImporting.value = true;
  errorMessage.value = "";

  try {
    const result = await datasetService.commitDatasetArchive({
      upload_token: preview.value.upload_token,
      name: name.value.trim(),
      description: description.value.trim(),
      exercise_type: exerciseType.value,
      purpose: purpose.value,
      primary_target: primaryTarget.value.trim(),
      secondary_target: secondaryTarget.value.trim(),
    });

    if (result.queue_failures.length > 0) {
      errorMessage.value =
        `${result.queue_failures.length} video(s) could not be queued. ` +
        "Inspect their status before training.";
    }

    emit(
      "imported",
      result.dataset.name,
      result.imported_videos,
    );

    emit("close");
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.message ||
      "Dataset import failed.";
  } finally {
    isImporting.value = false;
  }
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="import-overlay"
      @click.self="close"
    >
      <section
        class="import-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
      >
        <header class="import-header">
          <div>
            <span class="eyebrow">VECTOFIT DATA PIPELINE</span>
            <h2 id="import-title">Import Dataset</h2>
            <p>
              Upload a ZIP archive, review its manifest, then queue
              video processing.
            </p>
          </div>

          <button
            class="close-button"
            type="button"
            :disabled="isImporting || isPreviewing"
            @click="close"
          >
            ✕
          </button>
        </header>

        <div class="import-body">
          <section class="import-section">
            <h3>1. Dataset information</h3>

            <div class="form-grid">
              <label>
                Dataset name
                <input v-model="name" maxlength="50" required />
              </label>

              <label>
                Exercise
                <select v-model="exerciseType">
                  <option value="bodyweight_squat">
                    Bodyweight Squat
                  </option>
                  <option value="goblet_squat">
                    Goblet Squat
                  </option>
                </select>
              </label>

              <label>
                Purpose
                <select v-model="purpose">
                  <option value="training">Training</option>
                  <option value="evaluation">Evaluation</option>
                </select>
              </label>

              <label>
                Primary target
                <input v-model="primaryTarget" maxlength="50" required />
              </label>

              <label class="full-width">
                Description
                <textarea
                  v-model="description"
                  rows="2"
                />
              </label>
            </div>
          </section>

          <section class="import-section">
            <h3>2. Upload ZIP archive</h3>

            <p class="section-hint">
              Supported video formats: MP4, MOV, M4V, and AVI.
              The class and camera angle must be recognizable from
              folders or filenames.
            </p>

            <label class="file-picker">
              <span class="file-picker-icon">↑</span>
              <strong>
                {{ zipFile?.name || "Choose dataset ZIP" }}
              </strong>
              <small>
                {{ zipFile
                  ? `${(zipFile.size / 1024 / 1024).toFixed(1)} MB`
                  : "One archive containing your videos"
                }}
              </small>

              <input
                type="file"
                accept=".zip,application/zip"
                :disabled="isImporting || isPreviewing"
                @change="handleFileChange"
              />
            </label>

            <p class="section-hint">
              Good/bad labels are inherited by extracted repetitions.
              Ensure each clip consistently represents its folder label.
            </p>

            <button
              class="secondary-button"
              type="button"
              :disabled="!zipFile || isPreviewing || isImporting"
              @click="previewArchive"
            >
              {{ isPreviewing ? "Inspecting archive..." : "Preview archive" }}
            </button>
          </section>

          <section
            v-if="preview"
            class="import-section"
          >
            <h3>3. Review manifest</h3>

            <div class="manifest-summary">
              <div>
                <span>Recognized videos</span>
                <strong>{{ preview.file_count }}</strong>
              </div>

              <div>
                <span>Participants</span>
                <strong>{{ preview.participant_count }}</strong>
              </div>

              <div>
                <span>Good videos</span>
                <strong>{{ preview.by_label.good }}</strong>
              </div>

              <div>
                <span>Bad videos</span>
                <strong>{{ preview.by_label.bad }}</strong>
              </div>
            </div>

            <div class="angle-summary">
              <span>Diagonal: {{ preview.by_angle.diagonal }}</span>
              <span>Frontal: {{ preview.by_angle.frontal }}</span>
              <span>Sagittal: {{ preview.by_angle.sagittal }}</span>
            </div>

            <div
              v-if="preview.errors.length"
              class="message error"
            >
              <strong>Cannot import yet</strong>
              <ul>
                <li
                  v-for="item in preview.errors"
                  :key="item"
                >
                  {{ item }}
                </li>
              </ul>
            </div>

            <div
              v-if="preview.warnings.length"
              class="message warning"
            >
              <strong>Review these warnings</strong>
              <ul>
                <li
                  v-for="item in preview.warnings"
                  :key="item"
                >
                  {{ item }}
                </li>
              </ul>
            </div>

            <div
              v-if="preview.files.length"
              class="manifest-table-wrapper"
            >
              <table class="manifest-table">
                <thead>
                  <tr>
                    <th>Participant</th>
                    <th>View</th>
                    <th>Label</th>
                    <th>Archive path</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="file in preview.files"
                    :key="file.archive_path"
                  >
                    <td>{{ file.participant_code }}</td>
                    <td>{{ file.view_angle }}</td>
                    <td>
                      <span
                        :class="[
                          'label-chip',
                          file.source_label ? 'good' : 'bad',
                        ]"
                      >
                        {{ file.source_label ? "Good" : "Bad" }}
                      </span>
                    </td>
                    <td class="path-cell">{{ file.archive_path }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <p v-if="errorMessage" class="message error">
            {{ errorMessage }}
          </p>
        </div>

        <footer class="import-footer">
          <button
            class="secondary-button"
            type="button"
            :disabled="isImporting || isPreviewing"
            @click="close"
          >
            Cancel
          </button>

          <button
            class="primary-button"
            type="button"
            :disabled="!canImport"
            @click="commitImport"
          >
            {{ isImporting ? "Importing and queueing..." : "Import and process" }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.import-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  background: rgba(24, 24, 27, 0.55);
  backdrop-filter: blur(4px);
}

.import-modal {
  display: flex;
  flex-direction: column;
  width: min(100%, 1000px);
  max-height: 92vh;
  overflow: hidden;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 14px;
  background: var(--vf-surface, #ffffff);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.2);
  font-family: "Segoe UI", Arial, sans-serif;
}

.import-header,
.import-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.import-header {
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.import-header h2 {
  margin: 5px 0;
  font-size: 22px;
  color: var(--vf-dark, #18181b);
}

.import-header p,
.section-hint {
  margin: 0;
  color: var(--vf-muted, #71717a);
  font-size: 12px;
  line-height: 1.5;
}

.eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--vf-orange, #f97316);
}

.close-button {
  border: 0;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
}

.import-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.import-section + .import-section {
  margin-top: 24px;
  padding-top: 22px;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

.import-section h3 {
  margin: 0 0 13px;
  color: var(--vf-dark, #18181b);
  font-size: 14px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--vf-text, #27272a);
  font-size: 11px;
  font-weight: 700;
}

.form-grid input,
.form-grid select,
.form-grid textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 11px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 7px;
  background: #ffffff;
  color: var(--vf-text, #27272a);
  font: inherit;
  font-weight: 400;
}

.full-width {
  grid-column: 1 / -1;
}

.file-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 12px 0;
  padding: 24px;
  border: 1px dashed #fdba74;
  border-radius: 10px;
  background: #fffaf6;
  color: var(--vf-text, #27272a);
  cursor: pointer;
}

.file-picker input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.file-picker-icon {
  font-size: 26px;
  color: var(--vf-orange, #f97316);
}

.file-picker strong {
  max-width: 100%;
  overflow-wrap: anywhere;
  font-size: 12px;
}

.file-picker small {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.manifest-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.manifest-summary > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 13px;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 8px;
}

.manifest-summary span {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.manifest-summary strong {
  color: var(--vf-dark, #18181b);
  font-size: 21px;
}

.angle-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
}

.angle-summary span {
  padding: 7px 10px;
  border-radius: 6px;
  background: #f4f4f5;
}

.message {
  margin-top: 14px;
  padding: 12px;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.message.error {
  background: #fef2f2;
  color: #b91c1c;
}

.message.warning {
  background: #fff7ed;
  color: #9a3412;
}

.message ul {
  margin: 7px 0 0;
  padding-left: 19px;
}

.manifest-table-wrapper {
  max-height: 300px;
  margin-top: 14px;
  overflow: auto;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 8px;
}

.manifest-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}

.manifest-table th,
.manifest-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  text-align: left;
}

.manifest-table th {
  position: sticky;
  top: 0;
  background: #fafafa;
}

.path-cell {
  max-width: 340px;
  overflow-wrap: anywhere;
  color: var(--vf-muted, #71717a);
}

.label-chip {
  display: inline-block;
  padding: 4px 7px;
  border-radius: 5px;
  font-weight: 700;
}

.label-chip.good {
  background: #f0fdf4;
  color: #15803d;
}

.label-chip.bad {
  background: #fef2f2;
  color: #b91c1c;
}

.import-footer {
  justify-content: flex-end;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

@media (max-width: 700px) {
  .import-overlay {
    padding: 8px;
  }

  .import-header,
  .import-footer {
    padding: 16px;
  }

  .import-body {
    padding: 16px;
  }

  .form-grid,
  .manifest-summary {
    grid-template-columns: 1fr;
  }

  .import-footer {
    align-items: stretch;
    flex-direction: column-reverse;
  }
}
</style>
```

## 9. Frontend: connect it to the Datasets page

File: `vectofit_admin/src/pages/views/Datasets.vue`

Change the Vue import:

```
import { onMounted, ref } from "vue";
```

Add the component import:

```
import DatasetImportModal from "../../components/datasets/DatasetImportModal.vue";
```

Add these declarations in the script:

```
const isImportModalOpen = ref(false);

const openImportModal = () => {
  isImportModalOpen.value = true;
};

const handleBulkImported = async (
  datasetName: string,
  videoCount: number,
) => {
  successMessage.value =
    `Imported ${videoCount} video(s) into "${datasetName}". ` +
    "Video processing has been queued.";

  await fetchDatasets(true);
};
```

In the page header, replace the current single `Create Dataset` button with:

```TypeScript
<div class="page-actions">
  <button
    class="secondary-button"
    type="button"
    @click="openCreateModal"
  >
    Add Single Video
  </button>

  <button
    class="primary-button"
    type="button"
    @click="openImportModal"
  >
    <span class="button-icon">↑</span>
    Import Dataset ZIP
  </button>
</div>
```

At the bottom of the template, alongside the existing `CreateDatasetModal`, add:

```
<DatasetImportModal
  :is-open="isImportModalOpen"
  @close="isImportModalOpen = false"
  @imported="handleBulkImported"
/>
```

Add styles for the header action group:

```
.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 700px) {
  .page-actions {
    width: 100%;
    flex-direction: column;
  }

  .page-actions button {
    width: 100%;
  }
}
```

Keep the existing single-video modal and workflow. This gives you both the one-video testing path and the bulk-import path.

## 10. Test it in this order

Do not begin by importing all 26 participants. Validate the entire path using a tiny archive first.

Test 1: Preview a six-video ZIP

Use two participants, three angles, and at least one good/bad video per participant. Verify that the preview returns the correct participant codes, angle counts, labels, and warnings.

Test 2: Commit the import

Check that the database contains one parent `Dataset` and a `DatasetVideo` record for each uploaded video. Confirm that each child points to the correct participant and view angle.

Test 3: Process the videos

Confirm that each video reaches `READY` or `FAILED`, that extracted repetitions are linked to the child video, and that the parent collection reports the aggregate status.

Test 4: Train from the collection

Select the parent dataset in Training. Verify that `build_samples()` finds labelled repetitions from child videos and groups them by participant, not by video.

Run the backend tests after the migration:

```
python manage.py check
python manage.py makemigrations --check
python manage.py test apps.datasets
python manage.py test apps.training
```

Then build the admin frontend:

```
cd ..\vectofit_admin
npm run build
```

### Two deployment details to verify

First, your backend must have a running Celery worker and broker for queued video processing to happen. The import will create the records even if tasks cannot be queued, but those failures will be shown in the response and reflected in status.

Second, configure your Django server and any reverse proxy to accept ZIP uploads at the sizes you expect. The code defaults to a 4 GiB ZIP limit and a 20 GiB uncompressed-content limit; these can be changed through `DATASET_IMPORT_MAX_BYTES` and `DATASET_IMPORT_MAX_UNCOMPRESSED_BYTES` in your Django settings.

Expected result: one dataset collection containing your participant/video records, separate processing status per video, repetition-level samples linked to their source video, and a training loader that still preserves participant-level splitting. Once the small ZIP passes all four tests, import your full collection.
