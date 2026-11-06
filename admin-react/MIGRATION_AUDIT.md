# VectoFit React migration: Phase 0 audit

Date: 2026-11-06. Source: `../vectofit_admin/` (package name `vectofit_admin`). Branch: `admin-react-migration`.

## Stop before Phase 1: instruction conflicts

The requested behavior-preserving port conflicts with adding protected private routes: `src/router/index.ts` has no guards or auth metadata. Adding a token-based wrapper would introduce new navigation behavior. Recommendation: preserve private routing as written; implement only the existing public session guard. Obtain a scope decision before Phase 1, as explicitly required by the task.

There are **no Pinia stores** (`defineStore` has no matches). Pinia is installed and registered but all state lives in Vue composables or page components. Interpret the requested store migration as migrating those composables to React Query and local state; do not invent stores.

Private admin sign-out (`AdminLayout.vue:17`) only pushes `/login`, leaving the persisted token intact. Annotator private sign-out removes the token. A universal auth-store logout that clears the token would change existing admin behavior. Recommendation: preserve these distinct actions unless explicitly authorized to fix the inconsistency.

No implementation, dependencies, source copies, or builds have been performed. Vue/backend files remain untouched. Existing unrelated root changes were retained.

## Route table

Private means both default development/production and explicit `private` mode. Names below are Vue route names; public routes are unnamed.

| Path | Component or redirect | Layout | Name/meta/guard | Modes |
|---|---|---|---|---|
| `/` | Parent with no index child or redirect | AdminLayout | No guard | Private/default |
| `/dashboard` | dashboard/Dashboard | AdminLayout | Dashboard; no guard | Private/default |
| `/dataset` | views/Datasets | AdminLayout | Dataset; no guard | Private/default |
| `/dataset/:id/annotate` | views/DatasetAnnotation | AdminLayout | DatasetAnnotation; no guard; unrestricted id | Private/default |
| `/training` | views/Training | AdminLayout | Training; no guard | Private/default |
| `/evaluation` | Redirect by name to Models (`/models`) | AdminLayout | No guard | Private/default |
| `/models` | views/Models | AdminLayout | Models; no guard | Private/default |
| `/pilot-results` | views/PilotResults | AdminLayout | PilotResults; no guard | Private/default |
| `/annotator` | views/AnnotatorHome | AnnotatorLayout | AnnotatorHome; no guard | Private/default |
| `/annotator/:id` | views/DatasetAnnotation | AnnotatorLayout | AnnotatorDataset; unrestricted id; no guard | Private/default |
| `/login` | auth/Login | AuthLayout | Login; no guard | Private/default |
| `/register` | auth/Register | AuthLayout | Register; no guard | Private/default |
| `/` | Redirect `/annotator` | None | No guard | Public |
| `/annotator/login` | auth/PublicAuth | None | authPage: true | Public |
| `/annotator/register` | auth/PublicAuth | None | authPage: true | Public |
| `/annotator` | views/AnnotatorHome | AnnotatorLayout | Parent requiresAnnotator: true | Public |
| `/annotator/:id(\\d+)` | views/DatasetAnnotation | AnnotatorLayout | Inherits requiresAnnotator; numeric id | Public |
| catch-all | Inline `main` with 404 heading and Page not found text | None | No guard | Public |

Private has no explicit catch-all. Do not add a new private 404 or root redirect. Public beforeEach calls publicClient GET `me/` on every protected navigation; every failure redirects to `/annotator/login?next=<fullPath>`. React Router does not support Vue regex parameters: validate numeric ids before invoking the session guard to preserve the public 404. Public auth accepts next only if it matches `/^\/annotator(?:\/\d+)?(?:[?#].*)?$/`, otherwise `/annotator`; preserve replace vs push behavior.

## State inventory and React mapping

No Pinia state/getters/actions exist. Exact composable bodies, including returned interfaces, are in the source appendix below.

| Module | Server state/actions | Client state/derived values | Scope and migration |
|---|---|---|---|
| useDatasets | datasets, fetch, create/upload, retry, processing polling | search/filter inputs, summaries, loading/error messages | Shared refs; query list/detail, mutations and invalidation; preserve polling conditions |
| useParticipants | participants, fetchParticipants, createParticipant | creating/loading, error/success messages | Per-call refs; query/mutation; no newly invented edit/delete UI |
| useModels | registry, modelState, fetchModels/fetchModelState, activateModel | selectedModelId, initialization, messages, summaries | Shared refs; centralized list/state keys; keep knee_alignment/fppa_v2 filtering |
| useTraining | jobs/datasets, fetchTrainingData, refreshTrainingJobs, startTraining | selected job/datasets/angle/algorithm, features, hyperparameters, testSize, randomSeed, derived eligibility and summaries | Shared refs; active jobs poll 3000 ms; completion invalidates models; retain shared draft state across navigation |
| useEvaluation | registry/model state, fetch/select | selected id, formatting, summaries | Query reuse with equivalent loading/error behavior; page exists but route redirects to Models |
| useDatasetAnnotation | annotation session, load/save/clear | selected sample, rubric draft, validation, derived completion | Query per session; mutations must update cached sample/session; preserve draft reset and video behavior |
| useAnnotationPool | pool jobs/fetch | selection, filters, summary/formatters | Query pool jobs, local interaction state |
| useDashboard | Composes models/datasets/training | Dashboard totals/cards | Derived values from shared queries; avoid extra mutation of remote data |
| Login/Register | login/me/register requests | form, busy/error | Zustand token accessor retains localStorage key token; no refresh flow exists |
| PublicAuth | csrf/register/login | form, busy/error, validated next | Cookie session; store no public token; update CSRF default after login |
| AnnotatorHome/PilotResults | list/results fetched directly | loading/error | Dedicated useQuery keys |

React Query defaults (retry, focus refetch, freshness) can change observed timing. Configure per query to match existing explicit fetch/poll behavior. Some draft values currently live at module scope: use client-only shared state where necessary rather than resetting on each mount. Do not put server response copies into Zustand.

## HTTP clients and complete call inventory

URLs below are relative to the indicated client. Request/response contracts are source declarations, not runtime guarantees. Untyped Axios responses are marked untyped; do not invent backend shapes.

client baseURL: public/private `/api`; other modes VITE_API_URL or `http://127.0.0.1:8000/api`; VITE_API_BASE_URL overrides all modes. Request interceptor skips tokens only in public mode; otherwise reads localStorage token and writes `Authorization: Token <token>` with AxiosHeaders/fallback support. No response interceptor or refresh exists. Phase 2 must preserve client code except the required plain token accessor adaptation.

publicClient baseURL `/api/annotator/`, xsrfCookieName csrftoken, xsrfHeaderName X-CSRFToken; initializeCsrf sets common header from GET csrf response. Same-origin cookie behavior must remain intact.

| Module/function | Method | URL | Request | Response |
|---|---|---|---|---|
| accountService.getCurrentUser | GET | /accounts/me/ | none | CurrentUser |
| accountService.register | POST | /accounts/register/ | username,email,password,confirm_password,is_annotator | ignored; Promise<void> |
| annotationPoolService.getJobs | GET | /datasets/annotation-pool/ | none | AnnotationPoolJob[] |
| datasetAnnotationService.getSession | GET | public /annotator/datasets/${datasetId}/session/; otherwise /datasets/${datasetId}/annotation/ | none | AnnotationSession |
| datasetAnnotationService.save | PATCH | publicClient samples/${sampleId}/rating/; otherwise client /datasets/dataset-samples/${sampleId}/ | SaveAnnotationPayload | DatasetSample |
| datasetAnnotationService.clear | PATCH | same mode-specific sample URLs | {knee_annotation:null} | DatasetSample |
| datasetService.getDatasets | GET | /datasets/ | none | Dataset[] |
| datasetService.getDataset | GET | /datasets/${id}/ | none | Dataset |
| datasetService.getParticipants | GET | /datasets/participant/ | none | Participant[] |
| datasetService.createDatasetWithVideo | POST | /datasets/ | FormData | Dataset |
| datasetService.retryDataset | POST | /datasets/${id}/retry/ | none | Dataset |
| datasetService.previewDatasetArchive | POST | /datasets/import/preview/ | FormData zip_file: File | DatasetImportPreview, runtime validated |
| datasetService.commitDatasetArchive | POST | /datasets/import/ | DatasetBulkImportPayload | DatasetBulkImportResult |
| modelService.getModels | GET | /training/models/ | none | ModelRegistryRecord[] |
| modelService.activateModel | POST | /training/models/${id}/activate/ | none | ModelRegistryRecord |
| modelService.getModelState | GET | /training/models/${id}/state/ | none | ModelState |
| participantService.getParticipants | GET | /datasets/participant/ | none | Participant[] |
| participantService.createParticipant | POST | /datasets/participant/ | {} | Participant |
| participantService.getParticipant | GET | /datasets/participant/${id}/ | none | Participant |
| participantService.deleteParticipant | DELETE | /datasets/participant/${id}/ | none | ignored; Promise<void> |
| pilotResultsService.getResults | GET | /training/pilot-results/ | none | PilotResults (see exact function name in appendix) |
| trainingService.getTrainingJobs | GET | /training/jobs/ | none | TrainingJob[] |
| trainingService.startTraining | POST | /training/jobs/create/ | dataset_ids,algorithm,view_angle,prediction_target,feature_selection,hyperparameters,test_size,random_seed | TrainingJob |
| Login.handleLogin | POST | client /accounts/login/ | identifier,password | untyped; access_token or token |
| AnnotatorHome.fetchDatasets | GET | client public /annotator/datasets/; otherwise /datasets/annotation-datasets/ | none | AnnotationDataset[] {id,name} |
| public router guard | GET | publicClient me/ | none | untyped; status used |
| initializeCsrf | GET | publicClient csrf/ | none | untyped; csrfToken used |
| publicLogout | POST | publicClient logout/ | none; initializeCsrf first | ignored |
| PublicAuth.submit | POST | publicClient register/ | username,email,password,confirm_password,invitation_code | ignored; followed by login |
| PublicAuth.submit | POST | publicClient login/ | username,password | untyped; csrfToken used |

Both public sample mutations initialize CSRF first. Training feature and algorithm option functions are local constants, not HTTP calls. Every service's full type declarations and methods are retained in the appendix to disambiguate nested shapes.

## Build modes, styles, environment, and assets

`vite.config.ts` changes entry HTML before transformation: public replaces `/src/main.ts` with `/src/main.public.ts` and Administrator Portal with Annotation in the title. Both entries mount App and install Pinia/router/global CSS; only their router import differs. Output is dist-public only for public; every other mode outputs dist-private. No alias or define is configured in the source. Requested @ alias would be a target convenience, not something copied from this config. Proxy /api targets http://localhost:8000 with changeOrigin true and secure false.

The public generateBundle hook rejects modules matching layouts/AdminLayout, pages/dashboard, pages/views/(Training|Datasets|Models|PilotResults), or router/index. Preserve separate entry graphs (no eager private page imports from public entry), adapted extension names, and keep bundle inspection. Public/private route registration must be separated at build time.

MODE branches also occur in config/client.ts, services/datasetAnnotationService.ts, pages/views/AnnotatorHome.vue, pages/views/DatasetAnnotation.vue, and layouts/AnnotatorLayout.vue. DatasetAnnotation changes home navigation and its public flow; exact scripts are included below. No VITE flag controls route selection.

Only referenced VITE variables are VITE_API_URL and VITE_API_BASE_URL. Environment filenames and keys are listed below without values; env copies are deferred until Phase 1. No .env.public or .env.private was found in the source root. Vite standard dotenv/mode precedence is not customized.

Active global stylesheet: src/assets/styles/index.css, imported by both entries. It defines vf variables, resets, controls, focus styles, shared buttons/auth/page styles. src/style.css and assets/styles/variables.css are not imported by those entries; preserve their inactive status unless a traced import requires them. HTML loads Inter/Montserrat Google fonts and favicon.svg. Assets include hero.png, vite.svg, vue.svg, images/vectofit-tm.png, images/vectofit-tm2.png; public contains icons.svg and favicon.svg. Copy assets without changing paths/contents.

Scoped styles must become colocated modules. Vue scope attributes and CSS Modules have different descendant behavior: preserve global shared classes, component boundary selectors, dynamic classes, SVG rules, and specificity; do not mechanically hash every class. RouterLink active classes need explicit React mapping. Native video seeking/playback, nextTick timing, watch resets, and focus management need lifecycle translations and manual parity checks.

useDialogFocus traps Tab/Shift+Tab among visible enabled controls, captures/restores trigger, locks/restores body overflow, focuses after nextTick, and releases on unmount. React implementation should use refs/effects with cleanup, retaining those behaviors. Component callbacks replace emits, controlled values replace model updates; no chart library is needed (existing visualizations use native markup/SVG/CSS).

## Component inventory and exact source contracts

The generated inventory below includes every .vue file, its complete script (props, defaults, emits, imported composables and helpers), and slot outlets. Components with no props/emits have no external contract beyond router/children and their script. RouterView becomes Outlet; RouterLink becomes Link/NavLink. Unrouted files (Users, Settings, Participants, Evaluation, HelloWorld and supporting unused components) must not gain routes. Decide whether unused source components need full parity or are retained as unreachable equivalents; their existence is not permission to add navigation.

## Verification and next phase

This is a code-reading audit, not manual UI/API verification. No React build or parity claims are made. Phase 1 is paused by the user's explicit contradiction stop condition, not by a skill approval rule. Resolve private guard/logout behavior first. Proposed faithful scope: preserve private unguarded navigation and distinct logout actions; retain only public session guards. Then scaffold, copy framework-neutral modules, port shell and pages with per-phase/per-page commits, and perform all requested build/bundle/parity checks.

Existing Vue comparison command: `cd vectofit_admin; npm run dev -- --port 5173`. Proposed React comparison after implementation: `cd admin-react; npm run dev -- --port 5174`. For public comparison use `npm run dev:public -- --port 5173` and corresponding React port 5174. Django should run on port 8000. React commands are planned only: no runnable app exists yet.

## Environment inventory (values omitted)

### .env
- `VITE_API_URL`
### .env.example
- `VITE_API_URL`


## Vue component contracts (source snapshot)
### vectofit_admin/src/App.vue
```ts

```
Slot outlets: none.
### vectofit_admin/src/components/datasets/CreateDatasetModal.vue
```ts
import { useDialogFocus } from "../../composables/useDialogFocus";
import { computed, ref, watch, useTemplateRef } from "vue";
import type { CreateDatasetPayload } from "../../services/datasetService";
import type { Participant } from "../../services/participantService";

const props = defineProps<{
  isOpen: boolean;
  isSubmitting: boolean;
  form: CreateDatasetPayload;
  participants: Participant[];
}>();

const dialogRef = useTemplateRef<HTMLElement>("datasetDialog");
useDialogFocus(() => props.isOpen, dialogRef);

const emit = defineEmits<{
  (e: "close"): void;
  (e: "submit"): void;
  (e: "create-participant"): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const nameInputRef = ref<HTMLInputElement | null>(null);
const participantSelectRef = ref<HTMLSelectElement | null>(null);
const viewAngleSelectRef = ref<HTMLSelectElement | null>(null);

const fileError = ref("");
const formError = ref("");

const selectedFileName = computed(() => props.form.video_file?.name ?? "");

const canSubmit = computed(() => {
  return (
    !props.isSubmitting &&
    props.form.name.trim().length > 0 &&
    props.form.video_file !== null &&
    typeof props.form.participant === "number" &&
    [1, 2, 3].includes(props.form.view_angle ?? 0) &&
    !fileError.value
  );
});

watch(
  () => props.isOpen,
  (isOpen) => {
    formError.value = "";
    fileError.value = "";

    if (!isOpen) {
      props.form.video_file = null;

      if (fileInputRef.value) {
        fileInputRef.value.value = "";
      }
    }
  },
);

function closeModal() {
  if (props.isSubmitting) return;

  emit("close");
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  fileError.value = "";
  formError.value = "";

  props.form.video_file = null;

  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".mp4")) {
    fileError.value = "Please select an MP4 video file.";
    input.value = "";
    return;
  }

  props.form.video_file = file;
}

function handleSubmit() {
  formError.value = "";

  if (props.isSubmitting) return;

  if (!props.form.name.trim()) {
    formError.value = "Enter a dataset name.";
    nameInputRef.value?.focus();
    return;
  }

  if (!props.form.video_file || fileError.value) {
    fileError.value = fileError.value || "Select an MP4 video.";
    fileInputRef.value?.focus();
    return;
  }

  if (props.form.participant == null) {
    formError.value = "Select a participant.";
    participantSelectRef.value?.focus();
    return;
  }

  if (![1, 2, 3].includes(props.form.view_angle ?? 0)) {
    formError.value = "Select the video's view angle.";
    viewAngleSelectRef.value?.focus();
    return;
  }

  emit("submit");
}
```
Slot outlets: none.
### vectofit_admin/src/components/datasets/DatasetEmptyState.vue
```ts
defineProps<{
  title?: string
  description?: string
  buttonLabel?: string
}>()

const emit = defineEmits<{
  (e: 'action'): void
}>()
```
Slot outlets: none.
### vectofit_admin/src/components/datasets/DatasetImportModal.vue
```ts
import { useDialogFocus } from "../../composables/useDialogFocus";
import { computed, ref, watch, useTemplateRef } from "vue";
import {
  datasetService,
  type DatasetImportPreview,
} from "../../services/datasetService";

const props = defineProps<{ isOpen: boolean }>();

const dialogRef = useTemplateRef<HTMLElement>("datasetDialog");
useDialogFocus(() => props.isOpen, dialogRef);

const emit = defineEmits<{
  (event: "close"): void;
  (event: "imported", datasetName: string, videoCount: number): void;
}>();

type ReviewPolicy = "source" | "all" | "subset";
type SelectionMethod = "stratified" | "manual";

const DEFAULT_NAME = "VectoFit Bodyweight Squat v1";
const DEFAULT_DESCRIPTION =
  "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.";

const zipInput = ref<HTMLInputElement | null>(null);
const zipFile = ref<File | null>(null);
const preview = ref<DatasetImportPreview | null>(null);

const name = ref(DEFAULT_NAME);
const description = ref(DEFAULT_DESCRIPTION);
const exerciseType = ref("bodyweight_squat");
const purpose = ref("training");
const primaryTarget = ref("squat_quality");
const secondaryTarget = ref("biomechanical_errors");

const reviewPolicy = ref<ReviewPolicy>("subset");
const selectionMethod = ref<SelectionMethod>("stratified");
const reviewCount = ref(10);
const randomSeed = ref(42);
const selectedVideoPaths = ref<string[]>([]);

const isPreviewing = ref(false);
const isImporting = ref(false);
const importCompleted = ref(false);

const errorMessage = ref("");
const outcomeMessage = ref("");

const isBusy = computed(() => isPreviewing.value || isImporting.value);

const manifestFiles = computed(() => preview.value?.manifest.files ?? []);

const reviewableFiles = computed(() =>
  manifestFiles.value.filter((file) => Boolean(file.archive_path)),
);

const effectiveReviewCount = computed(() => {
  if (reviewPolicy.value === "source") return 0;
  if (reviewPolicy.value === "all") return reviewableFiles.value.length;

  return selectedVideoPaths.value.length;
});

const untouchedCount = computed(
  () => reviewableFiles.value.length - effectiveReviewCount.value,
);

const canGenerateSelection = computed(
  () =>
    reviewPolicy.value === "subset" &&
    selectionMethod.value === "stratified" &&
    reviewableFiles.value.length > 0,
);

const canImportReason = computed(() => {
  if (isBusy.value) return "Import is in progress.";
  if (importCompleted.value) return "This archive has already been imported.";
  if (!zipFile.value) return "Choose a ZIP archive to begin.";
  if (!name.value.trim()) return "Enter a dataset name.";

  if (!preview.value?.upload_token) {
    return "Preview the archive before importing.";
  }

  if (preview.value.manifest.errors.length > 0) {
    return "The archive has validation errors.";
  }

  if (reviewPolicy.value === "subset" && effectiveReviewCount.value === 0) {
    return "Select at least one video for manual review.";
  }

  return "";
});

const canImport = computed(() => !canImportReason.value);

function reset() {
  zipFile.value = null;
  preview.value = null;

  errorMessage.value = "";
  outcomeMessage.value = "";

  isPreviewing.value = false;
  isImporting.value = false;
  importCompleted.value = false;

  reviewPolicy.value = "subset";
  selectionMethod.value = "stratified";
  reviewCount.value = 10;
  randomSeed.value = 42;
  selectedVideoPaths.value = [];

  name.value = DEFAULT_NAME;
  description.value = DEFAULT_DESCRIPTION;
  exerciseType.value = "bodyweight_squat";
  purpose.value = "training";
  primaryTarget.value = "squat_quality";
  secondaryTarget.value = "biomechanical_errors";

  if (zipInput.value) zipInput.value.value = "";
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen && !isBusy.value) reset();
  },
);

function close() {
  if (isBusy.value) return;
  emit("close");
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  preview.value = null;
  selectedVideoPaths.value = [];
  errorMessage.value = "";
  outcomeMessage.value = "";
  importCompleted.value = false;

  if (!file) {
    zipFile.value = null;
    return;
  }

  if (!file.name.toLowerCase().endsWith(".zip")) {
    zipFile.value = null;
    input.value = "";
    errorMessage.value = "Please select a ZIP archive.";
    return;
  }

  zipFile.value = file;
}

function getErrorMessage(error: unknown): string | null {
  if (!error || typeof error !== "object") {
    return error instanceof Error ? error.message : null;
  }

  const candidate = error as {
    message?: unknown;
    response?: { data?: Record<string, unknown> };
  };

  const data = candidate.response?.data;

  for (const value of [
    data?.detail,
    data?.message,
    data?.error,
    ...Object.values(data ?? {}),
  ]) {
    if (typeof value === "string" && value.trim()) {
      return value;
    }

    if (Array.isArray(value)) {
      const message = value.find(
        (item): item is string =>
          typeof item === "string" && item.trim().length > 0,
      );

      if (message) return message;
    }
  }

  return typeof candidate.message === "string" ? candidate.message : null;
}

function hashString(value: string): number {
  let hash = 2166136261;

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return hash >>> 0;
}

function generateStratifiedSelection(): string[] {
  const files = reviewableFiles.value;
  if (!files.length) return [];

  const count = Math.max(
    1,
    Math.min(files.length, Math.floor(reviewCount.value)),
  );

  const groups = new Map<string, typeof files>();

  for (const file of files) {
    const label = file.source_label ? "good" : "bad";
    const angle = file.view_angle || "unknown";
    const key = `${label}:${angle}`;

    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(file);
  }

  const seed = String(randomSeed.value);

  for (const [key, group] of groups) {
    group.sort(
      (a, b) =>
        hashString(`${seed}:${key}:${a.archive_path}`) -
        hashString(`${seed}:${key}:${b.archive_path}`),
    );
  }

  const orderedGroups = [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, group]) => group);

  const selected: string[] = [];
  let cursor = 0;

  while (
    selected.length < count &&
    orderedGroups.some((group) => group.length > 0)
  ) {
    const group = orderedGroups[cursor % orderedGroups.length];

    if (group.length > 0) {
      selected.push(group.shift()!.archive_path);
    }

    cursor += 1;
  }

  return selected;
}

function generateSelection() {
  if (selectionMethod.value !== "stratified") return;

  selectedVideoPaths.value = generateStratifiedSelection();
}

function toggleVideo(path: string, checked: boolean) {
  if (checked) {
    if (!selectedVideoPaths.value.includes(path)) {
      selectedVideoPaths.value = [...selectedVideoPaths.value, path];
    }
  } else {
    selectedVideoPaths.value = selectedVideoPaths.value.filter(
      (item) => item !== path,
    );
  }
}

function toggleAllVideos() {
  const allPaths = reviewableFiles.value.map((file) => file.archive_path);

  selectedVideoPaths.value =
    selectedVideoPaths.value.length === allPaths.length ? [] : allPaths;
}

watch([reviewPolicy, selectionMethod], ([policy, method]) => {
  if (policy === "all") {
    selectedVideoPaths.value = reviewableFiles.value.map(
      (file) => file.archive_path,
    );
  } else if (policy === "source") {
    selectedVideoPaths.value = [];
  } else if (method === "stratified" && preview.value) {
    generateSelection();
  }
});

async function previewArchive() {
  if (isBusy.value) return;

  if (!zipFile.value) {
    errorMessage.value = "Select a ZIP archive first.";
    return;
  }

  isPreviewing.value = true;
  preview.value = null;
  selectedVideoPaths.value = [];
  errorMessage.value = "";
  outcomeMessage.value = "";

  try {
    const result = await datasetService.previewDatasetArchive(zipFile.value);

    preview.value = result;

    if (result.manifest.errors.length > 0) {
      errorMessage.value =
        "The archive has validation errors. Correct the archive and upload it again.";
    } else if (!result.upload_token) {
      errorMessage.value =
        "The preview did not return an upload token. Please preview again.";
    } else if (reviewPolicy.value === "subset") {
      generateSelection();
    } else if (reviewPolicy.value === "all") {
      selectedVideoPaths.value = reviewableFiles.value.map(
        (file) => file.archive_path,
      );
    }
  } catch (error: unknown) {
    errorMessage.value =
      getErrorMessage(error) ?? "Could not preview the archive.";
  } finally {
    isPreviewing.value = false;
  }
}

async function commitImport() {
  const currentPreview = preview.value;

  if (!currentPreview?.upload_token || !canImport.value) {
    return;
  }

  if (isBusy.value || importCompleted.value) return;

  if (!canImport.value) {
    errorMessage.value = canImportReason.value;
    return;
  }

  isImporting.value = true;
  errorMessage.value = "";
  outcomeMessage.value = "";

  try {
    const result = await datasetService.commitDatasetArchive({
      upload_token: currentPreview.upload_token,
      name: name.value.trim(),
      description: description.value.trim(),
      exercise_type: exerciseType.value,
      purpose: purpose.value,
      primary_target: primaryTarget.value.trim(),
      secondary_target: secondaryTarget.value.trim(),
      review_policy: reviewPolicy.value,
      selection_method: selectionMethod.value,
      review_count:
        reviewPolicy.value === "subset"
          ? effectiveReviewCount.value
          : undefined,
      random_seed:
        reviewPolicy.value === "subset" &&
        selectionMethod.value === "stratified"
          ? randomSeed.value
          : undefined,
      selected_video_paths:
        reviewPolicy.value === "subset" ? [...selectedVideoPaths.value] : [],
    });

    importCompleted.value = true;

    emit("imported", result.dataset.name, result.imported_videos);

    if (result.queue_failures.length > 0) {
      outcomeMessage.value =
        `Dataset "${result.dataset.name}" was imported, but ` +
        `${result.queue_failures.length} video(s) could not be queued. ` +
        `Imported: ${result.imported_videos}. ` +
        `Queued: ${result.queued_videos}. ` +
        "Check video processing statuses before training.";

      return;
    }

    emit("close");
  } catch (error: unknown) {
    errorMessage.value = getErrorMessage(error) ?? "Dataset import failed.";
  } finally {
    isImporting.value = false;
  }
}
```
Slot outlets: none.
### vectofit_admin/src/components/datasets/StructureGrid.vue
```ts
export interface StructureItem {
  id: string
  icon: string
  iconVariant: 'feature' | 'target' | 'error' | 'sample'
  title: string
  value: string
}

withDefaults(
  defineProps<{
    items?: StructureItem[]
  }>(),
  {
    items: () => [
      {
        id: 'features',
        icon: 'F',
        iconVariant: 'feature',
        title: 'Features',
        value: 'ROM, asymmetry, angles, velocity'
      },
      {
        id: 'primary-target',
        icon: 'C',
        iconVariant: 'target',
        title: 'Primary Target',
        value: 'Correct / Incorrect'
      },
      {
        id: 'secondary-target',
        icon: 'E',
        iconVariant: 'error',
        title: 'Secondary Targets',
        value: 'Biomechanical error labels'
      },
      {
        id: 'sample-unit',
        icon: 'R',
        iconVariant: 'sample',
        title: 'Sample Unit',
        value: 'One completed squat repetition'
      }
    ]
  }
)
```
Slot outlets: none.
### vectofit_admin/src/components/datasets/SummaryCard.vue
```ts
defineProps<{
  label: string
  value: string | number
  description: string
  icon: string
  variant?: 'samples' | 'correct' | 'incorrect' | 'version'
  statusIcon?: boolean
}>()
```
Slot outlets: none.
### vectofit_admin/src/components/evaluation/EvaluationConfigGrid.vue
```ts
import type {
  EvaluationModel,
  EvaluationMetric,
} from "../../hooks/useEvaluation";

interface Props {
  selectedDataset: Record<string, any> | null;
  selectedModelId: string | null;
  models: EvaluationModel[];
  metrics: EvaluationMetric[];
  summaryText: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "select-model", modelId: string): void;
  (e: "toggle-metric", metricId: string): void;
  (e: "start-evaluation"): void;
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/evaluation/EvaluationEmptyState.vue
```ts
const emit = defineEmits<{
  (e: "configure"): void;
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/evaluation/EvaluationModal.vue
```ts
import { ref, watch } from "vue";

interface Props {
  isOpen: boolean;
  datasetIds?: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "evaluation-started", payload: { evaluation_id: string }): void;
}>();

const selectedModel = ref("model-v2-4");
const selectedDataset = ref("");
const batchSize = ref(32);
const confidenceThreshold = ref(0.85);
const isSubmitting = ref(false);

watch(
  () => props.datasetIds,
  (newVal) => {
    if (newVal && newVal.length > 0) {
      selectedDataset.value = newVal[0];
    } else {
      selectedDataset.value = "ds-squat-benchmark-2026";
    }
  },
  { immediate: true },
);

const handleClose = () => {
  emit("close");
};

const handleSubmit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  try {
    await new Promise((resolve) => setTimeout(resolve, 600));
    const generatedId = `EVAL-JOB-${Math.floor(1000 + Math.random() * 9000)}`;
    emit("evaluation-started", { evaluation_id: generatedId });
    handleClose();
  } finally {
    isSubmitting.value = false;
  }
};
```
Slot outlets: none.
### vectofit_admin/src/components/evaluation/EvaluationTable.vue
```ts
import type { EvaluationRecord } from "../../hooks/useEvaluation";

defineProps<{
  evaluations: EvaluationRecord[];
}>();

const emit = defineEmits<{
  (e: "inspect", evaluation: EvaluationRecord): void;
  (e: "delete", id: string): void;
}>();

const getStatusClass = (status: EvaluationRecord["status"]) => {
  switch (status) {
    case "COMPLETED":
      return "badge-completed";
    case "RUNNING":
      return "badge-running";
    case "FAILED":
      return "badge-failed";
    case "PENDING":
      return "badge-pending";
    default:
      return "";
  }
};

const getScoreColor = (score: number) => {
  if (score >= 90) return "score-high";
  if (score >= 75) return "score-mid";
  return "score-low";
};
```
Slot outlets: none.
### vectofit_admin/src/components/evaluation/EvaluationWorkflow.vue
```ts
export interface WorkflowStep {
  stepNumber: number;
  title: string;
  description: string;
  status: "completed" | "active" | "pending";
}

defineProps<{
  steps: WorkflowStep[];
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/HelloWorld.vue
```ts
import { ref } from 'vue'
import heroImg from '../assets/hero.png'
import viteLogo from '../assets/vite.svg'
import vueLogo from '../assets/vue.svg'

const count = ref(0)
```
Slot outlets: none.
### vectofit_admin/src/components/models/ModelCard.vue
```ts
import { computed } from "vue";
import type { ModelCard } from "../../services/modelService";

const props = defineProps<{ card: ModelCard }>();

const statusLabel = computed(() => {
  switch (props.card.status) {
    case "ready":
      return "READY FOR ACTIVATION";
    case "warning":
      return "READY WITH WARNINGS";
    case "blocked":
      return "ACTIVATION BLOCKED";
    default:
      return String(props.card.status).toUpperCase();
  }
});

const targetLabel = computed(() => {
  return props.card.prediction_target === "knee_alignment"
    ? "Frontal-plane knee alignment"
    : "Unsupported model setup";
});

const classLabels = computed(() =>
  Object.entries(props.card.class_mapping)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([index, label]) => ({ index, label })),
);

const originEntries = computed(() =>
  Object.entries(props.card.data_provenance.label_origin_counts).sort(([a], [b]) =>
    a.localeCompare(b),
  ),
);

const shortHash = computed(() => {
  const hash = props.card.generated_from.manifest_sha256;
  return hash ? `${hash.slice(0, 12)}â€¦` : "not recorded";
});

const checkStatusLabel = (status: string) => {
  if (status === "pass") return "Pass";
  if (status === "warn") return "Warning";
  return "Blocked";
};
```
Slot outlets: none.
### vectofit_admin/src/components/models/ModelEvaluationState.vue
```ts
import { computed } from "vue";
import type { ModelState } from "../../services/modelService";

const props = defineProps<{
  evaluation: ModelState["evaluation"];
}>();

const metricLabels: Record<string, string> = {
  accuracy: "Accuracy",
  balanced_accuracy: "Balanced Accuracy",
  precision: "Precision",
  recall: "Recall",
  f1: "F1 Score",
};

const metricValue = (key: string) => {
  const value = props.evaluation[key as keyof ModelState["evaluation"]];

  return typeof value === "number" ? value : null;
};

const formatMetric = (value: number | null) =>
  value == null ? "â€”" : `${(value * 100).toFixed(1)}%`;

const classLabels = computed(() => {
  const mapping = props.evaluation.class_mapping ?? {};
  const matrix = props.evaluation.confusion_matrix ?? [];
  const size = Array.isArray(matrix) ? matrix.length : 0;

  return Array.from(
    { length: size },
    (_, index) => mapping[String(index)] ?? `Class ${index}`,
  );
});

const confusionMatrix = computed(() => {
  const matrix = props.evaluation.confusion_matrix;

  if (!Array.isArray(matrix) || matrix.length === 0) return null;
  if (!matrix.every((row) => Array.isArray(row) && row.length === matrix.length)) {
    return null;
  }

  return matrix;
});

const distributionRows = computed(() => {
  const overall = props.evaluation.overall_class_distribution ?? {};
  const test = props.evaluation.test_class_distribution ?? {};
  const mapping = props.evaluation.class_mapping ?? {};
  const mappingKeys = Object.keys(mapping).sort((a, b) => Number(a) - Number(b));

  if (mappingKeys.length) {
    return mappingKeys.map((key) => {
      const label = mapping[key];

      return {
        key,
        label,
        overall: overall[label] ?? overall[key] ?? "â€”",
        test: test[label] ?? test[key] ?? "â€”",
      };
    });
  }

  const keys = Array.from(
    new Set([...Object.keys(overall), ...Object.keys(test)]),
  ).sort((a, b) => a.localeCompare(b));

  return keys.map((key) => ({
    key,
    label: key,
    overall: overall[key] ?? "â€”",
    test: test[key] ?? "â€”",
  }));
});
```
Slot outlets: none.
### vectofit_admin/src/components/models/ModelFeatureState.vue
```ts
import { computed } from "vue";
import type { ModelState } from "../../services/modelService";

const props = defineProps<{
  features: ModelState["features"];
}>();

const featureLabels: Record<string, string> = {
  fppa_l_bottom: "Left FPPA at squat bottom",
  fppa_r_bottom: "Right FPPA at squat bottom",
  fppa_l_peak: "Left peak FPPA",
  fppa_r_peak: "Right peak FPPA",
  asym_bottom: "Bottom bilateral asymmetry",
  asym_peak: "Peak bilateral asymmetry",
};

const groups = computed(() => {
  const selected = new Set(props.features.selected);
  const fppaFeatures = [
    "fppa_l_bottom",
    "fppa_r_bottom",
    "fppa_l_peak",
    "fppa_r_peak",
    "asym_bottom",
    "asym_peak",
  ];

  return [
    {
      title: "FPPA v2 Â· M1 Input Features",
      features: fppaFeatures.filter((key) => selected.has(key)),
    },
  ].filter((group) => group.features.length > 0);
});

const importanceRows = computed(() =>
  Object.entries(props.features.importances)
    .map(([name, value]) => ({
      name,
      label: featureLabels[name] ?? name,
      value: Number(value),
    }))
    .filter((row) => Number.isFinite(row.value))
    .sort((a, b) => b.value - a.value),
);

const maxImportance = computed(() =>
  importanceRows.value.reduce((max, row) => Math.max(max, row.value), 0),
);

const labelFor = (name: string) => featureLabels[name] ?? name;
```
Slot outlets: none.
### vectofit_admin/src/components/models/ModelRegistryTable.vue
```ts
import type { ModelRegistryRecord } from "../../services/modelService";

defineProps<{
  models: ModelRegistryRecord[];
  selectedModelId: number | null;
}>();

defineEmits<{
  (event: "select", id: number): void;
}>();

const accuracy = (model: ModelRegistryRecord) => {
  const value = model.metrics?.accuracy;

  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "â€”";
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
```
Slot outlets: none.
### vectofit_admin/src/components/models/ModelsWorkflow.vue
```ts
export interface WorkflowStep {
  step: string;
  title: string;
  description: string;
}

defineProps<{
  steps: WorkflowStep[];
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/models/StatusBadge.vue
```ts
import type { DeploymentStatus } from "../../services/modelService";

defineProps<{
  status: DeploymentStatus;
  environment?: string;
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/AlgorithmSelector.vue
```ts

```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/DatasetSelector.vue
```ts
import { computed } from "vue";
import type { Dataset, ViewAngle } from "../../../services/datasetService";

type DatasetId = number;

const props = defineProps<{
  availableDatasets: Dataset[];
  filteredDatasets: Dataset[];
  selectedDatasetIds: DatasetId[];
  selectedDatasets: Dataset[];
  selectedViewAngle: ViewAngle | null;
}>();

const emit = defineEmits<{
  (event: "toggle-dataset", id: DatasetId): void;
}>();

const selectedCount = computed(() => props.selectedDatasets.length);

const statsFor = (dataset: Dataset) =>
  props.selectedViewAngle
    ? dataset.angle_training_stats?.[props.selectedViewAngle]
    : undefined;

const kneeExcludedLabels = [
  "borderline",
  "unassessable",
  "disputed",
  "missing",
] as const;

const kneeCount = (
  dataset: Dataset,
  label: "good" | "bad" | (typeof kneeExcludedLabels)[number],
) => Number(statsFor(dataset)?.knee_label_counts?.[label] ?? 0);

const kneeExcludedCount = (dataset: Dataset) =>
  kneeExcludedLabels.reduce(
    (total, label) => total + kneeCount(dataset, label),
    0,
  );

const selectedSamples = computed(() =>
  props.selectedDatasets.reduce(
    (total, dataset) => total + Number(statsFor(dataset)?.sample_count || 0),
    0,
  ),
);

const selectedLabelledSamples = computed(() =>
  props.selectedDatasets.reduce((total, dataset) => {
    const stats = statsFor(dataset);
    return total + Number(stats?.knee_target_sample_count || 0);
  }, 0),
);

const formatNumber = (value: number) => value.toLocaleString("en-US");
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/FeatureSelector.vue
```ts
import type { FeatureOption } from "../../../services/trainingService";

const props = defineProps<{
  features: FeatureOption[];
}>();

const featureDescriptions: Record<string, string> = {
  fppa_l_bottom: "Signed left knee angle at squat bottom.",
  fppa_r_bottom: "Signed right knee angle at squat bottom.",
  fppa_l_peak: "Largest absolute filtered left FPPA in the repetition.",
  fppa_r_peak: "Largest absolute filtered right FPPA in the repetition.",
  asym_bottom: "Absolute left-right FPPA difference at squat bottom.",
  asym_peak: "Absolute left-right difference between peak FPPA values.",
};
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/HyperparameterCard.vue
```ts
import { computed, ref } from "vue";

import ParameterSimulation from "./ParameterSimulation.vue";
import type { TrainingParameterDefinition } from "./trainingParameters";

const props = defineProps<{
  definition: TrainingParameterDefinition;
  modelValue: number;
}>();

const emit = defineEmits<{
  (event: "update", value: number): void;
}>();

const showHelp = ref(false);

const progress = computed(() => {
  const range = props.definition.max - props.definition.min;
  if (!range) return 0;
  return ((props.modelValue - props.definition.min) / range) * 100;
});

const displayValue = computed(() => {
  const value = props.modelValue;

  if (props.definition.format === "percent") {
    return `${Math.round(value * 100)}%`;
  }

  if (props.definition.format === "decimal") {
    return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }

  return Math.round(value).toLocaleString("en-US");
});

const updateValue = (rawValue: string | number) => {
  const numericValue = Number(rawValue);
  if (!Number.isFinite(numericValue)) return;

  const clamped = Math.min(
    props.definition.max,
    Math.max(props.definition.min, numericValue),
  );

  emit("update", clamped);
};
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/HyperparameterPanel.vue
```ts
import { computed } from "vue";

import HyperparameterCard from "./HyperparameterCard.vue";
import {
  FIXED_TRAINING_SETTINGS,
  TRAINING_PARAMETER_DEFINITIONS,
} from "./trainingParameters";

const props = defineProps<{
  hyperparameters: Record<string, unknown>;
  testSize: number;
  randomSeed: number;
}>();

const emit = defineEmits<{
  (event: "set-hyperparameter", payload: { key: string; value: number }): void;
  (event: "set-test-size", value: number): void;
  (event: "set-random-seed", value: number): void;
}>();

const valueFor = (key: string, fallback: number) => {
  const raw = props.hyperparameters[key];
  return typeof raw === "number" ? raw : fallback;
};

const parameterValues = computed(() =>
  Object.fromEntries(
    TRAINING_PARAMETER_DEFINITIONS.map((definition) => [
      definition.key,
      definition.target === "hyperparameter"
        ? valueFor(definition.key, definition.defaultValue)
        : definition.target === "testSize"
          ? props.testSize
          : props.randomSeed,
    ]),
  ),
);

const parameterGroups = [
  { title: "XGBoost Hyperparameters", definitions: TRAINING_PARAMETER_DEFINITIONS.filter((item) => item.target === "hyperparameter") },
  { title: "Experiment Settings", definitions: TRAINING_PARAMETER_DEFINITIONS.filter((item) => item.target !== "hyperparameter") },
];

const baselineDescription = computed(
  () =>
    "Use the displayed baseline values as the reproducible starting configuration. Change them when the experiment requires a deliberate comparison.",
);

const emitUpdate = (definitionKey: string, value: number) => {
  const definition = TRAINING_PARAMETER_DEFINITIONS.find(
    (item) => item.key === definitionKey,
  );
  if (!definition) return;

  if (definition.target === "hyperparameter") {
    emit("set-hyperparameter", { key: definition.key, value });
  } else if (definition.target === "testSize") {
    emit("set-test-size", value);
  } else {
    emit("set-random-seed", value);
  }
};
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/ParameterSimulation.vue
```ts
import type { ParameterSimulation } from "./trainingParameters";

const props = withDefaults(
  defineProps<{
    variant: ParameterSimulation;
    progress: number;
  }>(),
  { progress: 50 },
);

const clampedProgress = () => Math.min(100, Math.max(0, props.progress));
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/PredictionTargetSelector.vue
```ts
import type { PredictionTarget } from "../../../services/trainingService";
const props = defineProps<{ modelValue: PredictionTarget }>();
const emit = defineEmits<{ (event: "update:modelValue", value: PredictionTarget): void }>();
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/TrainingConfiguration.vue
```ts
import type { Dataset } from "../../../services/datasetService";
import type { FeatureOption } from "../../../services/trainingService";

import AlgorithmSelector from "./AlgorithmSelector.vue";
import DatasetSelector from "./DatasetSelector.vue";
import FeatureSelector from "./FeatureSelector.vue";
import HyperparameterPanel from "./HyperparameterPanel.vue";
import ViewAngleSelector from "./ViewAngleSelector.vue";

type ViewAngle = "diagonal" | "frontal" | "sagittal";
type DatasetId = number;

interface Props {
  availableDatasets: Dataset[];
  filteredDatasets: Dataset[];
  selectedDatasetIds: DatasetId[];
  selectedDatasets: Dataset[];
  selectedViewAngle: ViewAngle | null;
  features: FeatureOption[];
  hyperparameters: Record<string, unknown>;
  testSize: number;
  randomSeed: number;
  summaryText: string;
  canStartTraining: boolean;
  isTraining: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  (event: "toggle-dataset", id: DatasetId): void;
  (event: "set-hyperparameter", key: string, value: number): void;
  (event: "set-test-size", value: number): void;
  (event: "set-random-seed", value: number): void;
  (event: "start-training"): void;
}>();
```
Slot outlets: none.
### vectofit_admin/src/components/training/configuration/ViewAngleSelector.vue
```ts

```
Slot outlets: none.
### vectofit_admin/src/components/training/results/ConfusionMatrix.vue
```ts
import { computed } from "vue";

const props = defineProps<{
  matrix: unknown;
  labels?: string[] | null;
}>();

const entries = computed<number[][] | null>(() => {
  const matrix = props.matrix;

  if (!Array.isArray(matrix) || matrix.length === 0) {
    return null;
  }

  const size = matrix.length;
  const parsed: number[][] = [];

  for (const row of matrix) {
    if (!Array.isArray(row) || row.length !== size) {
      return null;
    }

    const values = row.map((value) => Number(value));
    if (values.some((value) => !Number.isFinite(value))) {
      return null;
    }

    parsed.push(values);
  }

  return parsed;
});

const matrixSize = computed(() => entries.value?.length ?? 0);

const classLabels = computed(() => {
  const size = matrixSize.value;
  const provided = (props.labels ?? []).filter(
    (label): label is string => typeof label === "string" && label.trim() !== "",
  );

  if (provided.length === size) {
    return provided;
  }

  if (size === 2) {
    return ["Bad", "Good"];
  }

  return Array.from({ length: size }, (_, index) => `Class ${index}`);
});

const humanize = (label: string) =>
  label
    .replace(/_/g, " ")
    .trim()
    .split(/\s+/)
    .map((word) =>
      word.length
        ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        : word,
    )
    .join(" ");

const rowTotal = (row: number[]) =>
  row.reduce((total, value) => total + value, 0);

const cellPercent = (rowIndex: number, columnIndex: number) => {
  const row = entries.value?.[rowIndex];
  if (!row) return 0;

  const total = rowTotal(row);
  return total > 0 ? Math.round((row[columnIndex] / total) * 100) : 0;
};

const summary = computed(() => {
  return "Rows are the human-reviewed FPPA labels (bad or good); columns are the model predictions. Inspect which knee-alignment class is confused before activating the model.";
});
```
Slot outlets: none.
### vectofit_admin/src/components/training/results/FeatureImportance.vue
```ts
const props = defineProps<{
  values: Array<{ name: string; value: number }>;
}>();

const maximum = () => Math.max(...props.values.map((item) => item.value), 0.000001);
```
Slot outlets: none.
### vectofit_admin/src/components/training/results/TrainingMetricInfo.vue
```ts
import { ref } from "vue";

withDefaults(
  defineProps<{
    title: string;
    value: string;
    question: string;
    description: string;
    interpretation: string;
    variant?: "default" | "primary";
  }>(),
  { variant: "default" },
);

const showInfo = ref(false);
```
Slot outlets: none.
### vectofit_admin/src/components/training/results/TrainingResult.vue
```ts
import { computed } from "vue";

import ConfusionMatrix from "./ConfusionMatrix.vue";
import FeatureImportance from "./FeatureImportance.vue";
import TrainingMetricInfo from "./TrainingMetricInfo.vue";

interface TrainingMetrics {
  accuracy?: number;
  balanced_accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  confusion_matrix?: unknown;
  target_names?: unknown;
  class_mapping?: unknown;
  prediction_target?: string;
  feature_importances?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TrainingResultJob {
  id: string | number;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | string;
  sample_count?: number | null;
  train_count?: number | null;
  test_count?: number | null;
  test_size?: number;
  completed_at?: string | null;
  started_at?: string | null;
  error_message?: string | null;
  metrics?: TrainingMetrics | null;
  hyperparameters?: Record<string, unknown> | null;
  feature_selection?: string[] | null;
  random_seed?: number | null;
  split_strategy?: string | null;
  dataset_names?: string[] | null;
  view_angle?: string | null;
  prediction_target?: string | null;
}

const props = defineProps<{
  job: TrainingResultJob | null;
}>();

const formatMetric = (value: unknown) => {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${(value * 100).toFixed(1)}%`;
};

const formatDate = (value: string | null | undefined) => {
  if (!value) return "--";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";

  return date.toLocaleString("en-PH", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const formatValue = (value: unknown) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value)
      ? String(value)
      : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  if (typeof value === "string" || typeof value === "boolean") {
    return String(value);
  }

  return "--";
};

const featureImportance = computed(() => {
  const raw = props.job?.metrics?.feature_importances;
  if (!raw || typeof raw !== "object") return [];

  return Object.entries(raw)
    .filter(([, value]) => typeof value === "number" && Number.isFinite(value))
    .map(([name, value]) => ({ name, value: Number(value) }))
    .sort((a, b) => b.value - a.value);
});

const confusionMatrix = computed(
  () => props.job?.metrics?.confusion_matrix ?? null,
);

const targetNames = computed(() => {
  const raw = props.job?.metrics?.target_names;

  if (Array.isArray(raw)) {
    const names = raw.filter(
      (value): value is string =>
        typeof value === "string" && value.trim() !== "",
    );
    if (names.length) return names;
  }

  const mapping = props.job?.metrics?.class_mapping;
  if (mapping && typeof mapping === "object") {
    return Object.keys(mapping as Record<string, unknown>)
      .sort((a, b) => Number(a) - Number(b))
      .map((key) => String((mapping as Record<string, unknown>)[key]));
  }

  return [];
});

const metricCopy = {
    balancedAccuracyDescription:
      "Balanced accuracy gives equal importance to good and bad knee-alignment labels.",
    precisionTitle: "Macro Precision",
    precisionQuestion:
      "How precise are predictions across good and bad knee-alignment labels?",
    precisionDescription:
      "Macro precision is the unweighted mean precision across the good and bad classes.",
    precisionInterpretation:
      "Each knee-alignment class contributes equally, so poor precision on either label lowers this score.",
    recallTitle: "Macro Recall",
    recallQuestion: "How well does the model identify both knee-alignment labels?",
    recallDescription:
      "Macro recall is the unweighted mean recall for good and bad knee-alignment labels.",
    recallInterpretation:
      "Each knee-alignment class contributes equally, so poor recall on either label lowers this score.",
    f1Title: "Macro F1",
  };

const usedParameters = computed(() => {
  const parameters: Array<{ label: string; value: string }> = [];
  const raw = props.job?.hyperparameters;

  if (raw && typeof raw === "object") {
    Object.entries(raw).forEach(([key, value]) => {
      if (
        typeof value === "number" ||
        typeof value === "string" ||
        typeof value === "boolean"
      ) {
        parameters.push({ label: key, value: formatValue(value) });
      }
    });
  }

  if (typeof props.job?.test_size === "number") {
    parameters.push({ label: "Requested test fraction", value: formatMetric(props.job.test_size) });
  }
  if (typeof props.job?.random_seed === "number") {
    parameters.push({
      label: "random_seed",
      value: String(props.job.random_seed),
    });
  }

  return parameters;
});

const featureLabels: Record<string, string> = {
  fppa_l_bottom: "Left FPPA at bottom",
  fppa_r_bottom: "Right FPPA at bottom",
  fppa_l_peak: "Left peak FPPA",
  fppa_r_peak: "Right peak FPPA",
  asym_bottom: "Bottom bilateral asymmetry",
  asym_peak: "Peak bilateral asymmetry",
};

const featureList = computed(() =>
  (props.job?.feature_selection ?? []).map(
    (feature) => featureLabels[feature] ?? feature,
  ),
);

const resultInterpretation = computed(() => {
  const f1 = props.job?.metrics?.f1;
  const balancedAccuracy = props.job?.metrics?.balanced_accuracy;

  if (typeof f1 !== "number" || typeof balancedAccuracy !== "number") {
    return "Review the available metrics, test-set counts, and confusion matrix before considering activation.";
  }

  return `The held-out test repetitions produced a macro F1 of ${formatMetric(f1)} and balanced accuracy of ${formatMetric(balancedAccuracy)}. Review both together with the confusion matrix before considering the trained FPPA model for activation.`;
});
```
Slot outlets: none.
### vectofit_admin/src/components/training/TrainingWorkflow.vue
```ts
import type { WorkflowStep } from "../../services/trainingService";

defineProps<{
  steps: WorkflowStep[];
}>();
```
Slot outlets: none.
### vectofit_admin/src/layouts/AdminLayout.vue
```ts
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const menuOpen = ref(false);
const navigation = [
  { to: '/dashboard', label: 'Overview', path: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z' },
  { to: '/dataset', label: 'Datasets', path: 'M3 7v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7 M3 7V5a2 2 0 0 1 2-2h5l2 4h9 M3 7h18 M8 12h8 M8 16h5' },
  { to: '/training', label: 'Training', path: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2' },
  { to: '/models', label: 'Model Registry', path: 'm12 3 9 5-9 5-9-5 9-5z M3 12l9 5 9-5 M3 16l9 5 9-5' },
  { to: '/pilot-results', label: 'Pilot Results', path: 'M9 3h6 M10 3v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-10V3 M8 15h8' },
];
const pageLabel = computed(() => route.name === 'DatasetAnnotation' ? 'Dataset annotation' : navigation.find(item => route.path.startsWith(item.to))?.label ?? 'Workspace');
watch(() => route.fullPath, () => { menuOpen.value = false; });
const handleSignOut = () => { router.push('/login'); };
```
Slot outlets: none.
### vectofit_admin/src/layouts/AnnotatorLayout.vue
```ts
import { useRouter } from "vue-router";
import { publicLogout } from "../config/publicAuth";
const router = useRouter();
import logo from "../assets/images/vectofit-tm2.png";

const signOut = async () => {
  if (import.meta.env.MODE === "public") {
    try {
      await publicLogout();
      await router.replace("/annotator/login");
    } catch {
      window.alert("Sign out failed. Please try again.");
    }
    return;
  }
  localStorage.removeItem("token");
  router.push("/login");
};
```
Slot outlets: none.
### vectofit_admin/src/layouts/AuthLayout.vue
```ts

```
Slot outlets: none.
### vectofit_admin/src/pages/auth/Login.vue
```ts
import { reactive, ref } from "vue";
import router from "../../router";
import client from "../../config/client";
import { accountService } from "../../services/accountService";

const isLoading = ref(false);
const loginError = ref("");

const form = reactive({
  identifier: "",
  password: "",
});

const handleLogin = async () => {
  if (isLoading.value) return;
  loginError.value = "";
  isLoading.value = true;

  try {
    const response = await client.post("/accounts/login/", {
      identifier: form.identifier,
      password: form.password,
    });

    const token = response.data.access_token || response.data.token;

    if (token) {
      localStorage.setItem("token", token);
      const user = await accountService.getCurrentUser();
      await router.push(user.is_annotator ? "/annotator" : "/dashboard");
    } else {
      loginError.value = "Sign-in could not be completed. Please try again.";
    }
  } catch {
    loginError.value = "Unable to sign in. Check your credentials and connection, then try again.";
  } finally {
    isLoading.value = false;
  }
};
```
Slot outlets: none.
### vectofit_admin/src/pages/auth/PublicAuth.vue
```ts
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { initializeCsrf, publicClient } from "../../config/publicAuth";

const route = useRoute();
const router = useRouter();
const registering = computed(() => route.path.endsWith("/register"));
const username = ref("");
const email = ref("");
const password = ref("");
const confirmation = ref("");
const invitation = ref("");
const error = ref("");
const busy = ref(false);
const next = computed(() => {
  const value = route.query.next;
  return typeof value === "string" && /^\/annotator(?:\/\d+)?(?:[?#].*)?$/.test(value)
    ? value : "/annotator";
});
async function submit() {
  busy.value = true;
  error.value = "";
  try {
    await initializeCsrf();
    if (registering.value) {
      await publicClient.post("register/", {
        username: username.value, email: email.value, password: password.value,
        confirm_password: confirmation.value, invitation_code: invitation.value,
      });
    }
    const { data } = await publicClient.post("login/", { username: username.value, password: password.value });
    publicClient.defaults.headers.common["X-CSRFToken"] = data.csrfToken;
    password.value = "";
    confirmation.value = "";
    invitation.value = "";
    await router.replace(next.value);
  } catch (err: unknown) {
    const response = (err as { response?: { data?: unknown } }).response;
    error.value = response?.data ? JSON.stringify(response.data) : "Unable to connect. Please try again.";
  } finally {
    busy.value = false;
  }
}
```
Slot outlets: none.
### vectofit_admin/src/pages/auth/Register.vue
```ts
import { reactive, ref } from "vue";
import router from "../../router";
import { accountService } from "../../services/accountService";

const form = reactive({
    username: '',
    email: '',
    password: '',
    confirmPassword: "",
    isAnnotator: true,
})

const error = ref<string | null>(null);
const isSubmitting = ref(false);

const handleRegister = async () => {
    if (isSubmitting.value) return;
    isSubmitting.value = true;
    error.value = null;
    try {
        await accountService.register({
            username: form.username,
            email: form.email,
            password: form.password,
            confirm_password: form.confirmPassword,
            is_annotator: form.isAnnotator,
        });
        await router.push("/login");
    } catch {
        error.value = "Registration failed. Check the form and try again.";
    } finally {
        isSubmitting.value = false;
    }
}
```
Slot outlets: none.
### vectofit_admin/src/pages/dashboard/Dashboard.vue
```ts
import { computed, onMounted, ref } from "vue";
import { useDashboard } from "../../hooks/useDashboard";
import SummaryCard from "../../components/datasets/SummaryCard.vue";

interface Props {
  eyebrowText?: string;
  pageTitle?: string;
  pageDescription?: string;
}

withDefaults(defineProps<Props>(), {
  eyebrowText: "VECTOFIT SYSTEM OVERVIEW",
  pageTitle: "Dashboard",
  pageDescription:
    "Datasets, model versions, and training activity in one research workspace.",
});

const { dashboardCards, currentModel, error, fetchAllDashboardData } = useDashboard();

const isRefreshing = ref(false);
const handleRefresh = async (force = true) => {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  try { await fetchAllDashboardData(force); }
  finally { isRefreshing.value = false; }
};

const formatMetric = (
  value: unknown,
  options?: { multiplier?: number; suffix?: string; decimals?: number },
): string => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }

  const { multiplier = 1, suffix = "", decimals = 1 } = options ?? {};

  return `${(value * multiplier).toFixed(decimals)}${suffix}`;
};

const modelAlgorithm = computed(() => currentModel.value?.algorithm ?? "N/A");

const modelLatency = computed(() =>
  formatMetric(currentModel.value?.metrics?.latencyMs, {
    suffix: " ms",
    decimals: 1,
  }),
);

const modelAccuracy = computed(() =>
  formatMetric(currentModel.value?.metrics?.accuracy, {
    multiplier: 100,
    suffix: "%",
    decimals: 1,
  }),
);

onMounted(() => {
  handleRefresh(false);
});
```
Slot outlets: none.
### vectofit_admin/src/pages/views/AnnotatorHome.vue
```ts
import { onMounted, ref } from "vue";
import client from "../../config/client";
import { useRouter } from "vue-router";

interface AnnotationDataset {
  id: number;
  name: string;
}

const router = useRouter();

const datasets = ref<AnnotationDataset[]>([]);
const error = ref<string | null>(null);
const isLoading = ref(true);

const fetchDatasets = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await client.get<AnnotationDataset[]>(
      import.meta.env.MODE === "public" ? "/annotator/datasets/" : "/datasets/annotation-datasets/",
    );

    datasets.value = response.data;
  } catch {
    error.value = "Unable to load annotation datasets.";
  } finally {
    isLoading.value = false;
  }
};

const openDataset = (id: number) => {
  router.push(`/annotator/${id}`);
};

onMounted(fetchDatasets);
```
Slot outlets: none.
### vectofit_admin/src/pages/views/DatasetAnnotation.vue
```ts
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDatasetAnnotation } from "../../hooks/useDatasetAnnotation";
import type {
  KneeAlignmentGrade,
  KneeDeviationDirection,
  SymmetryObservation,
} from "../../services/datasetAnnotationService";

const route = useRoute();
const router = useRouter();
const datasetHome = import.meta.env.MODE === "public" ? "/annotator" : "/dataset";

const videoRef = ref<HTMLVideoElement | null>(null);
const playbackRate = ref(1);
const videoError = ref("");
const reviewingCompleted = ref(false);
const kneeSides = ["left", "right"] as const;
const kneeGrades: KneeAlignmentGrade[] = [
  "aligned", "borderline", "deviated", "unassessable",
];

function handleDirectionChange(side: "left" | "right", event: Event) {
  setKneeDirection(
    side,
    (event.target as HTMLSelectElement).value as KneeDeviationDirection,
  );
}

function handleSymmetryChange(event: Event) {
  setSymmetryObservation(
    (event.target as HTMLSelectElement).value as SymmetryObservation,
  );
}

function handleNotesInput(event: Event) {
  setNotes((event.target as HTMLTextAreaElement).value);
}

const {
  session,
  samples,
  currentSample,
  currentIndex,
  fps,
  annotation,
  targetLabel,
  labelledCount,
  pendingReviewCount,
  isReviewComplete,
  currentSampleLabelState,
  isLoading,
  isSaving,
  error,
  load,
  setKneeGrade,
  setKneeDirection,
  setSymmetryObservation,
  setNotes,
  saveAndNext,
  clear,
  previous,
  next,
} = useDatasetAnnotation();

const activeVideo = computed(() => {
  const video = currentSample.value?.dataset_video;

  return video && typeof video === "object" ? video : null;
});

const activeVideoUrl = computed(
  () =>
    activeVideo.value?.video_url ?? session.value?.dataset.video_url ?? null,
);

const activeVideoLabel = computed(() => {
  const video = activeVideo.value;

  if (!video) {
    return "Dataset-level video";
  }

  if (import.meta.env.MODE === "public") {
    return [video.participant_code, video.view_angle_name].filter(Boolean).join(" / ");
  }

  const sourceLabel =
    video.source_label === true
      ? "GOOD FORM"
      : video.source_label === false
        ? "BAD FORM"
        : "UNKNOWN LABEL";

  return [
    video.participant_code ? `Participant ${video.participant_code}` : null,
    video.view_angle_name,
    `${sourceLabel}`,
  ]
    .filter(Boolean)
    .join(" Â· ");
});

const currentFps = computed(() => {
  const sampleFps = currentSample.value?.video_fps;

  return sampleFps != null && sampleFps > 0 ? sampleFps : fps.value;
});

const repStartTime = computed(() => {
  const startFrame = currentSample.value?.rep_assessment.start_frame;

  if (startFrame == null || currentFps.value <= 0) {
    return 0;
  }

  return startFrame / currentFps.value;
});

const repEndTime = computed(() => {
  const endFrame = currentSample.value?.rep_assessment.end_frame;

  if (endFrame == null || currentFps.value <= 0) {
    return null;
  }

  return endFrame / currentFps.value;
});

function seekToRep() {
  const video = videoRef.value;

  if (!video || video.readyState < HTMLMediaElement.HAVE_METADATA) {
    return;
  }

  video.currentTime = repStartTime.value;
}

function handleVideoLoadedMetadata() {
  const video = videoRef.value;

  if (!video) return;

  video.playbackRate = playbackRate.value;
  seekToRep();
}

function handleTimeUpdate() {
  const video = videoRef.value;

  if (
    !video ||
    repEndTime.value == null ||
    video.currentTime < repEndTime.value
  ) {
    return;
  }

  video.pause();
  seekToRep();
}

async function playRep() {
  const video = videoRef.value;

  if (!video || !activeVideoUrl.value) {
    return;
  }

  videoError.value = "";

  if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
    videoError.value = "The source video is still loading.";
    return;
  }

  video.playbackRate = playbackRate.value;
  seekToRep();

  try {
    await video.play();
  } catch (playError) {
    console.error("Could not play the current repetition.", playError);
    videoError.value = "Could not play this video. Please try again.";
  }
}

watch(
  () => currentSample.value?.id,
  async () => {
    videoRef.value?.pause();
    videoError.value = "";

    await nextTick();
    seekToRep();
  },
);

watch(playbackRate, (rate) => {
  if (videoRef.value) {
    videoRef.value.playbackRate = rate;
  }
});

const handleSaveNext = async () => {
  const saved = await saveAndNext();

  if (!saved || isReviewComplete.value) {
    return;
  }

  await nextTick();
  seekToRep();
};

onMounted(async () => {
  const datasetId = Number(route.params.id);

  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    await router.push(datasetHome);
    return;
  }

  await load(datasetId);
  await nextTick();
  seekToRep();

  requestAnimationFrame(seekToRep);
});
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Datasets.vue
```ts
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

import { useDatasets } from "../../hooks/useDatasets";
import { useParticipants } from "../../hooks/useParticipants.ts";
import { useAnnotationPool } from "../../hooks/useAnnotationPool";
import { VIEW_ANGLE_BY_ID, type Dataset } from "../../services/datasetService";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import DatasetEmptyState from "../../components/datasets/DatasetEmptyState.vue";
import StructureGrid from "../../components/datasets/StructureGrid.vue";
import CreateDatasetModal from "../../components/datasets/CreateDatasetModal.vue";
import DatasetImportModal from "../../components/datasets/DatasetImportModal.vue";

const router = useRouter();

const {
  datasets,
  isLoading,
  isCreating,
  isModalOpen,
  datasetForm,
  errorMessage,
  successMessage,
  totalDatasets,
  totalSamples,
  usableDatasets,
  fetchDatasets,
  openCreateModal,
  closeCreateModal,
  handleCreateDataset,
  retryDataset,
} = useDatasets();

const { participants, fetchParticipants, createParticipant } =
  useParticipants();
const {
  filteredJobs,
  selectedJob,
  search: annotationSearch,
  statusFilter: annotationStatusFilter,
  isLoading: isAnnotationPoolLoading,
  error: annotationPoolError,
  fetchJobs: fetchAnnotationJobs,
  selectJob,
  clearSelection,
} = useAnnotationPool();

const activeTab = ref<"datasets" | "annotation-pool">("datasets");

type DatasetReviewMetrics = {
  human_reviewed_sample_count?: number | null;
  review_selected_sample_count?: number | null;
  pending_review_sample_count?: number | null;
};

const reviewMetrics = (dataset: Dataset) =>
  dataset as Dataset & DatasetReviewMetrics;

const hasSamples = (dataset: Dataset) => dataset.sample_count > 0;

const hasUnlabelledSamples = (dataset: Dataset) =>
  dataset.sample_count > dataset.labelled_sample_count;

const humanReviewedSummary = (dataset: Dataset) => {
  const metrics = reviewMetrics(dataset);
  const reviewed = metrics.human_reviewed_sample_count;
  const selected = metrics.review_selected_sample_count;

  if (typeof reviewed !== "number" || !Number.isFinite(reviewed)) {
    return "Not tracked";
  }

  return typeof selected === "number" && Number.isFinite(selected)
    ? `${reviewed}/${selected}`
    : String(reviewed);
};

const zipReviewStatus = (dataset: Dataset): string => {
  const metrics = reviewMetrics(dataset);

  const selected = metrics.review_selected_sample_count;
  const reviewed = metrics.human_reviewed_sample_count;
  const pending = metrics.pending_review_sample_count;

  if (typeof selected !== "number" || !Number.isFinite(selected)) {
    return "Review tracking unavailable";
  }

  if (selected === 0) {
    return "No samples selected";
  }

  if (typeof pending === "number" && pending > 0) {
    return `${pending} pending review`;
  }

  if (
    typeof reviewed === "number" &&
    Number.isFinite(reviewed) &&
    reviewed >= selected
  ) {
    return "Review complete";
  }

  if (typeof reviewed === "number" && reviewed >= 0) {
    return "Review in progress";
  }

  return "Review status unavailable";
};

const isAnnotationReady = (dataset: Dataset) =>
  dataset.status === "READY" && hasSamples(dataset);

const isReviewComplete = (dataset: Dataset) => {
  if (!hasSamples(dataset)) return false;

  if (isZipCollection(dataset)) {
    const metrics = reviewMetrics(dataset);
    const selected = metrics.review_selected_sample_count;
    const reviewed = metrics.human_reviewed_sample_count;

    return (
      typeof selected === "number" &&
      selected > 0 &&
      typeof reviewed === "number" &&
      reviewed >= selected
    );
  }

  return !hasUnlabelledSamples(dataset);
};

const openAnnotation = (datasetId: number) => {
  router.push(`/dataset/${datasetId}/annotate`);
};

const handleAddParticipant = async () => {
  const participant = await createParticipant();

  if (participant) {
    datasetForm.value.participant = participant.id;
    console.log(`Created participant ${participant.participant_code}`);
  }
};

const handleRetryDataset = async (datasetId: number) => {
  await retryDataset(datasetId);
};

const processingDatasetCount = computed(
  () =>
    datasets.value.filter((dataset) => dataset.status === "PROCESSING").length,
);

const isImportModalOpen = ref(false);

const openImportModal = () => {
  isImportModalOpen.value = true;
};

const handleBulkImported = async (datasetName: string, videoCount: number) => {
  successMessage.value =
    `Imported ${videoCount} video(s) into "${datasetName}". ` +
    "Video processing has been queued.";

  await fetchDatasets(true);
};

function isZipCollection(dataset: Dataset): boolean {
  return !dataset.video_file && (dataset.video_count ?? 0) > 0;
}

function participantSummary(dataset: Dataset): string {
  if (isZipCollection(dataset)) {
    const count = dataset.participant_count;

    return count === null
      ? "Assigned per video"
      : `${count} participant${count === 1 ? "" : "s"}`;
  }

  return dataset.participant ? `p-${dataset.participant}` : "Unassigned";
}

function viewSummary(dataset: Dataset): string {
  if (isZipCollection(dataset)) {
    return dataset.view_angles?.length
      ? dataset.view_angles
          .map((angle) => angle.charAt(0).toUpperCase() + angle.slice(1))
          .join(",")
      : "Defined per video";
  }

  return dataset.view_angle == null
    ? ""
    : (VIEW_ANGLE_BY_ID[dataset.view_angle] ?? "Unknown");
}

function videoSummary(dataset: Dataset): string {
  if (!isZipCollection(dataset)) {
    return dataset.video_file ? "1 video" : "";
  }

  const total = dataset.video_count ?? 0;
  const ready = dataset.ready_video_count ?? 0;
  const failed = dataset.failed_video_count ?? 0;

  return `${ready}/${total} ready - ${failed} failed`;
}

function formatActivityDate(value: string): string {
  return new Date(value).toLocaleString();
}

function annotationStatusLabel(status: string): string {
  return status.replace("_", " ");
}

onMounted(async () => {
  await Promise.all([
    fetchParticipants(),
    fetchDatasets(),
    fetchAnnotationJobs(),
  ]);
});
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Evaluation.vue
```ts
import { computed } from "vue";
import { useEvaluation } from "../../hooks/useEvaluation";

const {
  models,
  selectedModelId,
  modelState,
  evaluation,
  training,
  summaryCards,
  evaluationAvailable,
  isLoading,
  isStateLoading,
  error,
  selectModel,
  fetchModels,
  formatPercent,
  formatDate,
  formatAngle,
  formatTarget,
} = useEvaluation();

const confusionMatrix = computed(
  () => evaluation.value?.confusion_matrix ?? [],
);

const classDistribution = computed(() =>
  Object.entries(evaluation.value?.test_class_distribution ?? {}),
);

const selectedDatasetNames = computed(
  () => training.value?.dataset_names ?? [],
);

const selectedFeatures = computed(
  () => modelState.value?.features.selected ?? [],
);

const featureWarnings = computed(
  () => modelState.value?.feature_warnings ?? [],
);

const handleModelChange = async (event: Event) => {
  const value = (event.target as HTMLSelectElement).value;
  const id = Number(value);

  if (Number.isInteger(id) && id > 0) {
    await selectModel(id);
  }
};
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Models.vue
```ts
import { computed } from "vue";
import { useModels } from "../../hooks/useModels";
import ModelCard from "../../components/models/ModelCard.vue";
import ModelEvaluationState from "../../components/models/ModelEvaluationState.vue";
import ModelFeatureState from "../../components/models/ModelFeatureState.vue";
import ModelRegistryTable from "../../components/models/ModelRegistryTable.vue";

const {
  models,
  modelState,
  selectedModelId,
  summaryCards,
  isLoading,
  isStateLoading,
  error,
  isActivatingModel,
  activationMessage,
  selectModel,
  activateModel,
} = useModels();

const statusLabel = computed(() => {
  const model = modelState.value;

  if (!model) return "NO MODEL";

  return model.is_active ? "ACTIVE" : "REGISTERED";
});

const canActivateModel = computed(() => {
  const model = modelState.value;

  if (!model) return false;

  if (model.model_card) {
    return !model.is_active && model.model_card.activation.allowed;
  }

  return (
    !model.is_active &&
    Boolean(model.view_angle) &&
    model.training.status === "COMPLETED" &&
    model.artifact_available
  );
});

const activationBlockers = computed(
  () => modelState.value?.model_card?.activation.blockers ?? [],
);

const predictionTargetLabel = computed(() => {
  return modelState.value?.prediction_target === "knee_alignment"
    ? "Frontal-plane knee alignment"
    : "Unsupported model setup";
});

const cameraAngleLabel = computed(() => {
  const angle = modelState.value?.view_angle;

  if (!angle) return "Unspecified";

  return angle.charAt(0).toUpperCase() + angle.slice(1);
});

const selectedDatasetText = computed(() => {
  const datasetNames = modelState.value?.training.dataset_names ?? [];

  return datasetNames.length ? datasetNames.join(", ") : "No dataset recorded";
});

const evaluationAvailable = computed(() => {
  const model = modelState.value;

  if (
    !model ||
    model.training.status !== "COMPLETED" ||
    model.training.test_count <= 0
  ) {
    return false;
  }

  const evaluation = model.evaluation;

  return [
    evaluation.accuracy,
    evaluation.balanced_accuracy,
    evaluation.precision,
    evaluation.recall,
    evaluation.f1,
  ].some((metric) => metric != null);
});

const formatDate = (value: string | null | undefined): string => {
  if (!value) return "â€”";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "â€”";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Participants.vue
Empty source file; no component implementation.
Slot outlets: none.
### vectofit_admin/src/pages/views/PilotResults.vue
```ts
import { onMounted, ref } from "vue";
import {
  pilotResultsService,
  type PilotMetricResult,
  type PilotResults,
} from "../../services/pilotResultsService";

const results = ref<PilotResults | null>(null);
const error = ref<string | null>(null);
const isLoading = ref(true);

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
const formatInterval = (value: number) => `${value.toFixed(3)}`;

const loadResults = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    results.value = await pilotResultsService.getResults();
  } catch {
    error.value = "No pilot results are available. Run run_m0_m1 first.";
  } finally {
    isLoading.value = false;
  }
};

const participantRows = (result: PilotMetricResult) => result.per_participant;

onMounted(loadResults);
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Settings.vue
Empty source file; no component implementation.
Slot outlets: none.
### vectofit_admin/src/pages/views/Training.vue
```ts
import { computed, ref } from "vue";
import type { TrainingJob } from "../../services/trainingService";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import TrainingConfiguration from "../../components/training/configuration/TrainingConfiguration.vue";
import TrainingResult from "../../components/training/results/TrainingResult.vue";
import { useTraining } from "../../hooks/useTraining";

const configurationSection = ref<HTMLElement | null>(null);

const {
  features,
  selectedDatasets,
  selectedDatasetIds,
  selectedViewAngle,
  hyperparameters,
  testSize,
  randomSeed,
  summaryCards,
  configSummaryText,
  canStartTraining,
  isLoading,
  isTraining,
  error,
  toggleDataset,
  setHyperparameter,
  setTestSize,
  setRandomSeed,
  startTraining,
  availableDatasets,
  filteredDatasets,
  trainingJobs,
  selectedJob,
  selectJob,
} = useTraining();

const handleStartTraining = async () => {
  const job = await startTraining();
  if (job) {
    selectJob(job.id);
  }
};

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString();

const selectedJobId = computed<number | null>({
  get: () => selectedJob.value?.id ?? null,
  set: (jobId) => {
    if (jobId !== null) {
      selectJob(jobId);
    }
  },
});

const latestJob = computed<TrainingJob | null>(() => selectedJob.value);

const configurationStatus = computed(() => {
  if (isTraining.value) return "TRAINING";
  return canStartTraining.value ? "READY" : "INCOMPLETE";
});

const scrollToConfiguration = () => {
  configurationSection.value?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
};
```
Slot outlets: none.
### vectofit_admin/src/pages/views/Users.vue
Empty source file; no component implementation.
Slot outlets: none.
## Service and composable contracts (source snapshot)
### vectofit_admin/src/composables/useDialogFocus.ts
```ts
import { nextTick, onBeforeUnmount, watch, type Ref } from "vue";

export function useDialogFocus(isOpen: () => boolean, dialogRef: Readonly<Ref<HTMLElement | null>>) {
  let trigger: HTMLElement | null = null;
  let previousOverflow = "";
  let active = false;
  const focusable = () => Array.from(dialogRef.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  ) ?? []).filter(element => element.getClientRects().length > 0);

  const containFocus = (event: KeyboardEvent) => {
    if (event.key !== "Tab") return;
    const elements = focusable();
    const first = elements[0];
    const last = elements[elements.length - 1];
    if (!first || !last) { event.preventDefault(); dialogRef.value?.focus(); return; }
    if (!dialogRef.value?.contains(document.activeElement) ||
        (event.shiftKey && document.activeElement === first) ||
        (!event.shiftKey && document.activeElement === last)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  };
  const release = () => {
    if (!active) return;
    active = false;
    document.removeEventListener("keydown", containFocus);
    document.body.style.overflow = previousOverflow;
    if (trigger?.isConnected) trigger.focus();
  };
  watch(isOpen, async open => {
    if (!open) { release(); return; }
    trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    previousOverflow = document.body.style.overflow;
    active = true;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", containFocus);
    await nextTick();
    if (isOpen()) (focusable()[0] ?? dialogRef.value)?.focus();
  });
  onBeforeUnmount(release);
}
```
### vectofit_admin/src/hooks/useAnnotationPool.ts
```ts
import { computed, ref } from "vue";
import {
  annotationPoolService,
  type AnnotationPoolJob,
} from "../services/annotationPoolService";

export function useAnnotationPool() {
  const jobs = ref<AnnotationPoolJob[]>([]);
  const selectedJobId = ref<number | null>(null);
  const search = ref("");
  const statusFilter = ref("ALL");
  const isLoading = ref(false);
  const error = ref("");

  const selectedJob = computed(
    () => jobs.value.find((job) => job.id === selectedJobId.value) ?? null,
  );

  const filteredJobs = computed(() => {
    const query = search.value.trim().toLowerCase();

    return jobs.value.filter((job) => {
      const matchesSearch =
        !query ||
        job.name.toLowerCase().includes(query) ||
        job.annotators.some((summary) =>
          summary.annotator?.username.toLowerCase().includes(query),
        );
      const matchesStatus =
        statusFilter.value === "ALL" ||
        job.job_status === statusFilter.value;

      return matchesSearch && matchesStatus;
    });
  });

  const fetchJobs = async () => {
    isLoading.value = true;
    error.value = "";

    try {
      jobs.value = await annotationPoolService.getJobs();

      if (
        selectedJobId.value !== null &&
        !jobs.value.some((job) => job.id === selectedJobId.value)
      ) {
        selectedJobId.value = null;
      }
    } catch (requestError) {
      console.error("Failed to load annotation pool:", requestError);
      error.value = "Unable to load annotation activity.";
    } finally {
      isLoading.value = false;
    }
  };

  const selectJob = (job: AnnotationPoolJob) => {
    selectedJobId.value = job.id;
  };

  const clearSelection = () => {
    selectedJobId.value = null;
  };

  return {
    jobs,
    filteredJobs,
    selectedJob,
    search,
    statusFilter,
    isLoading,
    error,
    fetchJobs,
    selectJob,
    clearSelection,
  };
}
```
### vectofit_admin/src/hooks/useDashboard.ts
```ts
import { computed } from "vue";

import { useModels } from "./useModels";
import { useDatasets } from "./useDatasets";
import { useTraining } from "./useTraining";

export function useDashboard() {
  const { models, fetchModels, error: modelError } = useModels();

  const { datasets, fetchDatasets, errorMessage: datasetError } = useDatasets();

  const { trainingJobs, fetchTrainingData, error: trainingError } = useTraining();

  const currentModel = computed(
    () =>
      models.value.find((model) => model.is_active) ?? models.value[0] ?? null,
  );

  const activeJobsCount = computed(
    () =>
      trainingJobs.value.filter(
        (job) => job.status === "RUNNING" || job.status === "PENDING",
      ).length,
  );

  const dashboardCards = computed(() => [
    {
      label: "Registered Datasets",
      value: datasets.value.length,
      description: "Available benchmark datasets",
      icon: "D",
      variant: "samples" as const,
    },

    {
      label: "Registered Models",
      value: models.value.length,
      description: "Total trained model versions",
      icon: "M",
      variant: "version" as const,
    },

    {
      label: "Current Model",
      value: currentModel.value ? `v${currentModel.value.version}` : "None",
      description: currentModel.value?.name ?? "No registered model",
      icon: "M",
      variant: "correct" as const,
    },

    {
      label: "Active Training Runs",
      value: activeJobsCount.value,
      description: "Currently executing pipeline jobs",
      icon: "T",
      variant: "samples" as const,
    },
  ]);

  const error = computed(() => [modelError.value, datasetError.value, trainingError.value].filter(Boolean).join(" "));

  const fetchAllDashboardData = async (force = false) => {
    datasetError.value = "";
    await Promise.all([fetchModels(force), fetchDatasets(force), fetchTrainingData(force)]);
  };

  return {
    error,
    dashboardCards,
    currentModel,
    fetchAllDashboardData,
  };
}
```
### vectofit_admin/src/hooks/useDatasetAnnotation.ts
```ts
import { computed, ref } from "vue";
import {
  datasetAnnotationService,
  emptyKneeAnnotation,
  type DatasetSample,
  type AnnotationSession,
  type KneeAnnotation,
  type KneeAlignmentGrade,
  type KneeDeviationDirection,
  type SymmetryObservation,
  type TargetLabel,
} from "../services/datasetAnnotationService";

type SampleAnnotationState = "manual" | "inherited" | "unlabeled";

function isManuallyAnnotated(sample: DatasetSample): boolean {
  return sample.knee_annotation != null;
}

function deriveTargetLabel(annotation: KneeAnnotation): TargetLabel | null {
  const left = annotation.left.grade;
  const right = annotation.right.grade;

  if (left === null || right === null) {
    return null;
  }

  if (left === "deviated" || right === "deviated") {
    return "bad";
  }

  if (left === "unassessable" || right === "unassessable") {
    return "unassessable";
  }

  if (left === "borderline" || right === "borderline") {
    return "borderline";
  }

  return "good";
}

function mergeSavedSample(
  original: DatasetSample,
  saved: DatasetSample,
): DatasetSample {
  const savedVideo = saved.dataset_video;

  const datasetVideo =
    savedVideo !== null && typeof savedVideo === "object"
      ? savedVideo
      : original.dataset_video;

  return {
    ...original,
    ...saved,
    dataset_video: datasetVideo,
    video_fps: saved.video_fps ?? original.video_fps ?? null,
  };
}

export function useDatasetAnnotation() {
  const session = ref<AnnotationSession | null>(null);
  const currentIndex = ref(0);
  const annotation = ref<KneeAnnotation>(emptyKneeAnnotation());

  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);

  const currentSample = computed<DatasetSample | null>(
    () => session.value?.samples[currentIndex.value] ?? null,
  );

  const samples = computed(() => session.value?.samples ?? []);
  const fps = computed(() => session.value?.fps ?? 0);

  const targetLabel = computed<TargetLabel | null>(() =>
    deriveTargetLabel(annotation.value),
  );

  const currentSampleLabelState = computed<SampleAnnotationState | null>(() => {
    const sample = currentSample.value;

    if (!sample) return null;
    if (isManuallyAnnotated(sample)) return "manual";

    if (sample.is_correct != null) return "inherited";

    return "unlabeled";
  });

  const labelledCount = computed(
    () => samples.value.filter(isManuallyAnnotated).length,
  );

  const inheritedLabelCount = computed(
    () =>
      samples.value.filter(
        (sample) => !isManuallyAnnotated(sample) && sample.is_correct != null,
      ).length,
  );

  const pendingReviewCount = computed(
    () => samples.value.length - labelledCount.value,
  );

  const isReviewComplete = computed(
    () => samples.value.length > 0 && pendingReviewCount.value === 0,
  );

  const loadCurrentSample = () => {
    const sample = currentSample.value;

    annotation.value =
      sample?.knee_annotation != null
        ? JSON.parse(JSON.stringify(sample.knee_annotation))
        : emptyKneeAnnotation();
  };

  const load = async (datasetId: number) => {
    isLoading.value = true;
    error.value = null;

    try {
      session.value = await datasetAnnotationService.getSession(datasetId);
      currentIndex.value = Math.max(0, session.value.samples.findIndex(sample => sample.knee_annotation == null));
      loadCurrentSample();
    } catch (err) {
      console.error(err);
      error.value = "Unable to load annotation data.";
    } finally {
      isLoading.value = false;
    }
  };

  const setKneeGrade = (
    side: "left" | "right",
    grade: KneeAlignmentGrade | null,
  ) => {
    annotation.value[side].grade = grade;

    if (grade === null || grade === "unassessable") {
      annotation.value[side].direction = null;
    } else if (grade === "aligned") {
      annotation.value[side].direction = "none";
    } else if (
      annotation.value[side].direction === null ||
      annotation.value[side].direction === "none"
    ) {
      annotation.value[side].direction = "uncertain";
    }
  };

  const setKneeDirection = (
    side: "left" | "right",
    direction: KneeDeviationDirection,
  ) => {
    annotation.value[side].direction = direction;
  };

  const setSymmetryObservation = (value: SymmetryObservation) => {
    annotation.value.symmetry_observation = value;
  };

  const setNotes = (value: string) => {
    annotation.value.notes = value;
  };

  const save = async (): Promise<boolean> => {
    const sample = currentSample.value;

    if (isSaving.value) return false;
    if (!sample || targetLabel.value === null) {
      error.value = "Assess both knees before saving.";
      return false;
    }

    isSaving.value = true;
    error.value = null;

    try {
      const payload: KneeAnnotation = JSON.parse(JSON.stringify(annotation.value));
      const saved = await datasetAnnotationService.save(sample.id, {
        knee_annotation: payload,
      });

      if (session.value) {
        session.value.samples[currentIndex.value] = mergeSavedSample(sample, {
          ...saved,
          knee_annotation: saved.knee_annotation ?? payload,
          target_label: saved.target_label ?? targetLabel.value,
        });
      }

      return true;
    } catch (err) {
      console.error(err);
      error.value = "Failed to save knee annotation.";
      return false;
    } finally {
      isSaving.value = false;
    }
  };

  const findPendingIndex = (start: number, end: number) => {
    for (let index = start; index < end; index += 1) {
      const sample = samples.value[index];
      if (sample && !isManuallyAnnotated(sample)) return index;
    }
    return -1;
  };

  const saveAndNext = async () => {
    if (!(await save())) return false;

    if (isReviewComplete.value) return true;

    let nextIndex = findPendingIndex(
      currentIndex.value + 1,
      samples.value.length,
    );

    if (nextIndex === -1) {
      nextIndex = findPendingIndex(0, currentIndex.value + 1);
    }

    if (nextIndex !== -1) {
      currentIndex.value = nextIndex;
      loadCurrentSample();
    }

    return true;
  };

  const clear = async () => {
    const sample = currentSample.value;
    if (!sample || isSaving.value) return;

    isSaving.value = true;
    error.value = null;

    try {
      const cleared = await datasetAnnotationService.clear(sample.id);

      if (session.value) {
        session.value.samples[currentIndex.value] = mergeSavedSample(sample, {
          ...cleared,
          knee_annotation: null,
          target_label: null,
        });
      }

      loadCurrentSample();
    } catch (err) {
      console.error(err);
      error.value = "Failed to clear knee annotation.";
    } finally {
      isSaving.value = false;
    }
  };

  const previous = () => {
    if (isSaving.value || currentIndex.value <= 0) return;
    currentIndex.value -= 1;
    loadCurrentSample();
  };

  const next = () => {
    if (isSaving.value || currentIndex.value >= samples.value.length - 1) return;
    currentIndex.value += 1;
    loadCurrentSample();
  };

  return {
    session,
    samples,
    currentSample,
    currentIndex,
    fps,
    annotation,
    targetLabel,
    labelledCount,
    inheritedLabelCount,
    pendingReviewCount,
    isReviewComplete,
    currentSampleLabelState,
    isLoading,
    isSaving,
    error,
    load,
    setKneeGrade,
    setKneeDirection,
    setSymmetryObservation,
    setNotes,
    save,
    saveAndNext,
    clear,
    previous,
    next,
  };
}
```
### vectofit_admin/src/hooks/useDatasets.ts
```ts
import { ref, computed, watch, onUnmounted } from "vue";
import {
  datasetService,
  type Dataset,
  type Participant,
  type CreateDatasetPayload,
} from "../services/datasetService";

export function useDatasets() {
  const datasets = ref<Dataset[]>([]);
  const participants = ref<Participant[]>([]);

  const isLoading = ref(false);
  const isRefreshing = ref(false);
  const isInitialized = ref(false);
  const isCreating = ref(false);
  const isModalOpen = ref(false);

  const errorMessage = ref("");
  const successMessage = ref("");

  const isPolling = ref(false);

  const datasetForm = ref<CreateDatasetPayload>({
    name: "",
    description: "",
    participant: 0,
    exercise_type: "bodyweight_squat",
    purpose: "training",
    primary_target: "squat_quality",
    secondary_target: "biomechanical_errors",
    view_angle: null,
    video_file: null,
  });

  const fetchDatasets = async (force = false) => {
    if (isInitialized.value && !force) {
      return;
    }

    if (force) {
      isRefreshing.value = true;
    } else {
      isLoading.value = true;
    }

    try {
      datasets.value = await datasetService.getDatasets();
      isInitialized.value = true;
    } catch (error) {
      console.error("Failed to load datasets:", error);
      errorMessage.value = "Unable to load datasets.";

      if (!isInitialized.value) {
        isInitialized.value = false;
      }
    } finally {
      if (force) {
        isRefreshing.value = false;
      } else {
        isLoading.value = false;
      }
    }
  };

  const fetchParticipants = async () => {
    try {
      participants.value = await datasetService.getParticipants();
    } catch (error) {
      console.error("Failed to load participants:", error);
      errorMessage.value = "Unable to load participants.";
    }
  };

  const refreshDatasets = () => fetchDatasets(true);

  let processingPollInterval: ReturnType<typeof setInterval> | null = null;

  const stopProcessingPolling = () => {
    if (processingPollInterval !== null) {
      clearInterval(processingPollInterval);
      processingPollInterval = null;
    }
  };

  const pollProcessingState = async () => {
    const hasProcessingDatasets = datasets.value.some(
      (dataset) => dataset.status === "PROCESSING",
    );

    if (!hasProcessingDatasets) {
      stopProcessingPolling();
      return;
    }

    try {
      await fetchDatasets(true);
    } catch (error) {
      console.error("Failed to poll dataset processing state:", error);
    }
  };

  const startProcessingPolling = () => {
    if (processingPollInterval !== null) {
      return;
    }

    processingPollInterval = setInterval(() => {
      void pollProcessingState();
    }, 3000);
  };

  watch(
    () => datasets.value.some((dataset) => dataset.status === "PROCESSING"),
    (hasProcessingDatasets) => {
      if (hasProcessingDatasets) {
        startProcessingPolling();
      } else {
        stopProcessingPolling();
      }
    },
  );

  onUnmounted(() => {
    stopProcessingPolling();
  });

  const resetDatasetForm = () => {
    datasetForm.value = {
      name: "",
      description: "",
      participant: 0,
      exercise_type: "bodyweight_squat",
      purpose: "training",
      primary_target: "squat_quality",
      secondary_target: "biomechanical_errors",
      view_angle: null,
      video_file: null,
    };
  };

  const openCreateModal = () => {
    resetDatasetForm();

    errorMessage.value = "";
    successMessage.value = "";

    isModalOpen.value = true;
  };

  const closeCreateModal = () => {
    if (isCreating.value) {
      return;
    }

    isModalOpen.value = false;
  };

  const handleCreateDataset = async () => {
    if (!datasetForm.value.name.trim()) {
      errorMessage.value = "Dataset name is required.";
      return false;
    }

    if (!datasetForm.value.video_file) {
      errorMessage.value = "Please select a video.";
      return false;
    }

    if (!datasetForm.value.participant) {
      errorMessage.value = "Please assign a participant.";
      return false;
    }

    isCreating.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
      const formData = new FormData();

      formData.append("name", datasetForm.value.name.trim());

      if (datasetForm.value.description) {
        formData.append("description", datasetForm.value.description);
      }

      formData.append("exercise_type", datasetForm.value.exercise_type);
      formData.append("purpose", datasetForm.value.purpose);
      formData.append("primary_target", datasetForm.value.primary_target);
      formData.append("participant", String(datasetForm.value.participant));

      if (datasetForm.value.secondary_target) {
        formData.append("secondary_target", datasetForm.value.secondary_target);
      }

      if (datasetForm.value.view_angle !== null) {
        formData.append("view_angle", String(datasetForm.value.view_angle));
      }

      formData.append("video_file", datasetForm.value.video_file);

      await datasetService.createDatasetWithVideo(formData);

      successMessage.value = "Dataset created successfully.";

      resetDatasetForm();
      isModalOpen.value = false;

      await refreshDatasets();

      return true;
    } catch (error: any) {
      console.error("Failed to create dataset:", error);
      console.error(
        "Backend response:",
        JSON.stringify(error?.response?.data, null, 2),
      );

      errorMessage.value =
        JSON.stringify(error?.response?.data) || "Failed to create dataset.";

      return false;
    } finally {
      isCreating.value = false;
    }
  };

  const retryDataset = async (id: number) => {
    errorMessage.value = "";
    successMessage.value = "";

    try {
      await datasetService.retryDataset(id);

      successMessage.value = "Dataset processing restarted.";

      await refreshDatasets();

      return true;
    } catch (error: any) {
      console.error("Failed to retry dataset:", error);
      console.error(
        "Backend response:",
        JSON.stringify(error?.response?.data, null, 2),
      );

      errorMessage.value =
        JSON.stringify(error?.response?.data) || "Failed to retry dataset.";

      return false;
    }
  };

  const totalDatasets = computed(() => datasets.value.length);

  const totalSamples = computed(() =>
    datasets.value.reduce(
      (total, dataset) => total + (dataset.sample_count || 0),
      0,
    ),
  );

  const totalCorrect = computed(() =>
    datasets.value.reduce((total) => total + 0, 0),
  );

  const totalIncorrect = computed(() => 0);

  const usableDatasets = computed(() =>
    datasets.value.filter((dataset) => dataset.is_usable_for_training),
  );

  onUnmounted(() => {
    stopProcessingPolling();
  });

  return {
    datasets,
    participants,
    isLoading,
    isInitialized,
    isCreating,
    isModalOpen,
    isPolling,
    datasetForm,
    errorMessage,
    successMessage,

    totalDatasets,
    totalSamples,
    totalCorrect,
    totalIncorrect,
    usableDatasets,

    fetchDatasets,
    fetchParticipants,
    refreshDatasets,
    retryDataset,

    startProcessingPolling,
    stopProcessingPolling,

    openCreateModal,
    closeCreateModal,
    handleCreateDataset,
  };
}
```
### vectofit_admin/src/hooks/useEvaluation.ts
```ts
import { computed, onMounted, ref } from "vue";
import {
  modelService,
  type ModelRegistryRecord,
  type ModelState,
} from "../services/modelService";

export interface EvaluationModel {
  id: string;
  name: string;
  version: string;
  type: string;
  accuracy?: number;
}

export interface EvaluationMetric {
  id: string;
  name: string;
  category: string;
  description: string;
  selected: boolean;
}

export interface EvaluationRecord {
  id: string;
  modelName: string;
  datasetName: string;
  score: number;
  status: "COMPLETED" | "RUNNING" | "FAILED" | "PENDING";
  createdAt: string;
  duration: string;
}

export function useEvaluation() {
  const models = ref<ModelRegistryRecord[]>([]);
  const modelState = ref<ModelState | null>(null);
  const selectedModelId = ref<number | null>(null);

  const isLoading = ref(false);
  const isStateLoading = ref(false);
  const error = ref<string | null>(null);

  const messageFromError = (err: unknown, fallback: string): string => {
    if (typeof err === "object" && err !== null && "response" in err) {
      const response = (err as { response?: { data?: unknown } }).response
        ?.data;

      if (typeof response === "object" && response !== null) {
        const data = response as Record<string, unknown>;

        for (const key of ["detail", "error_message", "message"]) {
          if (typeof data[key] === "string" && data[key]) {
            return data[key] as string;
          }
        }
      }
    }

    return err instanceof Error ? err.message : fallback;
  };

  const selectedModel = computed(
    () =>
      models.value.find((model) => model.id === selectedModelId.value) ?? null,
  );

  const evaluation = computed(() => modelState.value?.evaluation ?? null);
  const training = computed(() => modelState.value?.training ?? null);

  const evaluationAvailable = computed(
    () =>
      training.value?.status === "COMPLETED" &&
      evaluation.value?.accuracy != null,
  );

  const summaryCards = computed(() => {
    const metrics = evaluation.value;

    const formatPercent = (value: number | null | undefined) =>
      value == null ? "â€”" : `${(value * 100).toFixed(1)}%`;

    return [
      {
        label: "ACCURACY",
        value: formatPercent(metrics?.accuracy),
        description: "Correct predictions on the held-out test set",
      },
      {
        label: "BALANCED ACCURACY",
        value: formatPercent(metrics?.balanced_accuracy),
        description: "Average recall across classes",
      },
      {
        label: "PRECISION",
        value: formatPercent(metrics?.precision),
        description: "Precision reported by the training evaluation",
      },
      {
        label: "F1 SCORE",
        value: formatPercent(metrics?.f1),
        description: "F1 reported by the training evaluation",
      },
    ];
  });

  const selectModel = async (id: number) => {
    if (selectedModelId.value === id && modelState.value?.id === id) {
      return;
    }

    selectedModelId.value = id;
    modelState.value = null;
    isStateLoading.value = true;
    error.value = null;

    try {
      modelState.value = await modelService.getModelState(id);
    } catch (err: unknown) {
      error.value = messageFromError(
        err,
        "Failed to load evaluation results for this model.",
      );
    } finally {
      isStateLoading.value = false;
    }
  };

  const fetchModels = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      models.value = (await modelService.getModels()).filter(
        (model) =>
          model.prediction_target === "knee_alignment" &&
          model.feature_schema_version === "fppa_v2",
      );

      if (!models.value.length) {
        selectedModelId.value = null;
        modelState.value = null;
        return;
      }

      const initialModel =
        models.value.find((model) => model.is_active) ?? models.value[0];

      await selectModel(initialModel.id);
    } catch (err: unknown) {
      error.value = messageFromError(err, "Failed to load the Model Registry.");
    } finally {
      isLoading.value = false;
    }
  };

  const formatPercent = (value: number | null | undefined) =>
    value == null ? "â€”" : `${(value * 100).toFixed(1)}%`;

  const formatDate = (value: string | null | undefined) => {
    if (!value) return "â€”";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
      ? "â€”"
      : new Intl.DateTimeFormat(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(date);
  };

  const formatAngle = (value: string | null | undefined) => {
    if (!value) return "Not specified";

    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  const formatTarget = (value: string | null | undefined) => {
    return value === "knee_alignment"
      ? "Frontal-plane knee alignment"
      : "Unsupported model setup";
  };

  onMounted(fetchModels);

  return {
    models,
    selectedModel,
    selectedModelId,
    modelState,
    evaluation,
    training,
    summaryCards,
    evaluationAvailable,
    isLoading,
    isStateLoading,
    error,
    selectModel,
    fetchModels,
    formatPercent,
    formatDate,
    formatAngle,
    formatTarget,
  };
}
```
### vectofit_admin/src/hooks/useModels.ts
```ts
import { ref, computed, onMounted } from "vue";
import {
  modelService,
  type ModelState,
  type ModelRegistryRecord,
} from "../services/modelService";

const models = ref<ModelRegistryRecord[]>([]);
const modelState = ref<ModelState | null>(null);
const selectedModelId = ref<number | null>(null);

const isLoading = ref<boolean>(false);
const isStateLoading = ref(false);
const isActivatingModel = ref(false);
const activationMessage = ref<string | null>(null);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export const invalidateModels = () => {
  isInitialized.value = false;
};

const messageFromError = (err: unknown, fallback: string): string => {
  const responseData =
    typeof err === "object" && err !== null && "response" in err
      ? (err as { response?: { data?: unknown } }).response?.data
      : undefined;
  if (typeof responseData === "object" && responseData !== null) {
    const data = responseData as Record<string, unknown>;
    for (const key of ["detail", "error_message", "message"]) {
      if (typeof data[key] === "string" && data[key])
        return data[key] as string;
    }
  }
  return err instanceof Error ? err.message : fallback;
};

const fetchModelState = async (id: number) => {
  isStateLoading.value = true;
  error.value = null;

  try {
    modelState.value = await modelService.getModelState(id);
  } catch (err: unknown) {
    error.value = messageFromError(err, "Failed to load model state.");

    modelState.value = null;
  } finally {
    isStateLoading.value = false;
  }
};

export function useModels() {
  const fetchModels = async (force = false) => {
    if (isInitialized.value && !force) return;

    isLoading.value = true;
    error.value = null;

    try {
      models.value = (await modelService.getModels()).filter(
        (model) =>
          model.prediction_target === "knee_alignment" &&
          model.feature_schema_version === "fppa_v2",
      );

      const active = models.value.find((model) => model.is_active);
      const nextId = active?.id ?? models.value[0]?.id ?? null;

      selectedModelId.value = nextId;

      if (nextId != null) {
        await fetchModelState(nextId);
      } else {
        modelState.value = null;
      }

      isInitialized.value = true;
    } catch (err: unknown) {
      error.value = messageFromError(err, "Failed to load model registry.");

      isInitialized.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  const selectModel = async (id: number) => {
    if (selectedModelId.value === id && modelState.value?.id === id) {
      return;
    }

    selectedModelId.value = id;
    await fetchModelState(id);
  };

  const activateModel = async (id: number) => {
    isActivatingModel.value = true;
    activationMessage.value = null;
    error.value = null;
    try {
      await modelService.activateModel(id);
      await fetchModels(true);
      selectedModelId.value = id;
      await fetchModelState(id);
      activationMessage.value =
        "Model activated for its camera angle and prediction target.";
    } catch (err: unknown) {
      error.value = messageFromError(err, "Failed to activate model.");
    } finally {
      isActivatingModel.value = false;
    }
  };

  const selectedModel = computed(
    () =>
      models.value.find((model) => model.id === selectedModelId.value) ?? null,
  );

  const summaryCards = computed(() => {
    const state = modelState.value;
    const metrics = state?.evaluation;

    return [
      {
        label: "CURRENT VERSION",
        value: state ? `v${state.version}` : "â€”",
        description: state?.name ?? "No model registered",
      },
      {
        label: "ACCURACY",
        value:
          metrics?.accuracy != null
            ? `${(metrics.accuracy * 100).toFixed(1)}%`
            : "â€”",
        description: metrics ? "Held out test set" : "No evaluation available",
      },
      {
        label: "F1 SCORE",
        value: metrics?.f1 != null ? `${(metrics.f1 * 100).toFixed(1)}%` : "â€”",
        description: metrics
          ? "Macro-averaged F1 across good and bad FPPA labels"
          : "No evaluation available",
      },
      {
        label: "FEATURES",
        value: state?.features.selected.length ?? "â€”",
        description: "Model input features",
      },
    ];
  });

  onMounted(() => fetchModels(true));

  return {
    models,
    modelState,
    selectedModel,
    selectedModelId,
    isLoading,
    isStateLoading,
    isActivatingModel,
    activationMessage,
    isInitialized,
    error,
    summaryCards,
    fetchModels,
    fetchModelState,
    selectModel,
    activateModel,
  };
}
```
### vectofit_admin/src/hooks/useParticipants.ts
```ts
import { ref } from "vue";
import {
  participantService,
  type Participant,
} from "../services/participantService";

export function useParticipants() {
  const participants = ref<Participant[]>([]);

  const isLoading = ref(false);
  const isCreating = ref(false);

  const errorMessage = ref("");
  const successMessage = ref("");

  const fetchParticipants = async () => {
    isLoading.value = true;
    errorMessage.value = "";

    try {
      participants.value = await participantService.getParticipants();
    } catch (error) {
      console.error("Failed to load participants:", error);
      errorMessage.value = "Unable to load participants.";
    } finally {
      isLoading.value = false;
    }
  };

  const createParticipant = async () => {
    isCreating.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
      const participant = await participantService.createParticipant();

      participants.value.push(participant);

      successMessage.value = `Participant ${participant.participant_code} created.`;

      return participant;
    } catch (error: any) {
      console.error("Failed to create participant:", error);

      errorMessage.value =
        error?.response?.data?.detail ||
        error?.response?.data?.participant_code?.[0] ||
        "Failed to create participant.";

      return null;
    } finally {
      isCreating.value = false;
    }
  };

  return {
    participants,
    isLoading,
    isCreating,
    errorMessage,
    successMessage,
    fetchParticipants,
    createParticipant,
  };
}
```
### vectofit_admin/src/hooks/useTraining.ts
```ts
import { computed, onMounted, onUnmounted, ref } from "vue";
import { invalidateModels } from "./useModels";
import {
  type AlgorithmOption,
  type FeatureOption,
  trainingService,
  type TrainingJob,
} from "../services/trainingService";
import { datasetService, type Dataset } from "../services/datasetService";

const trainingJobs = ref<TrainingJob[]>([]);

const selectedJob = ref<TrainingJob | null>(null);

const selectJob = (jobId: number) => {
  const job = trainingJobs.value.find((j) => j.id === jobId);
  if (job) {
    selectedJob.value = job;
  }
};
const datasets = ref<Dataset[]>([]);
const features = ref<FeatureOption[]>([]);
const algorithms = ref<AlgorithmOption[]>([]);

const selectedDatasetIds = ref<number[]>([]);
const selectedViewAngle = ref<ViewAngle | null>("frontal");
const selectedAlgorithmId = ref<string>("xgboost");

const hyperparameters = ref<Record<string, unknown>>({});
const testSize = ref<number>(0.3);
const randomSeed = ref<number>(42);

const isLoading = ref(false);
const isSubmitting = ref(false);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

const responseDataFor = (err: unknown): unknown =>
  typeof err === "object" && err !== null && "response" in err
    ? (err as { response?: { data?: unknown } }).response?.data
    : undefined;

const setErrorState = (err: unknown) => {
  const responseData = responseDataFor(err);

  if (typeof responseData === "object" && responseData !== null) {
    const data = responseData as Record<string, unknown>;
    for (const key of ["detail", "error_message", "message"]) {
      if (typeof data[key] === "string" && data[key]) {
        error.value = data[key] as string;
        return;
      }
    }

    const messages: string[] = [];
    const collect = (value: unknown, prefix: string) => {
      if (typeof value === "string") {
        messages.push(prefix ? `${prefix}: ${value}` : value);
      } else if (Array.isArray(value)) {
        value.forEach((item) => collect(item, prefix));
      } else if (typeof value === "object" && value !== null) {
        Object.entries(value as Record<string, unknown>).forEach(
          ([key, item]) => collect(item, prefix ? `${prefix}.${key}` : key),
        );
      }
    };
    collect(data, "");
    if (messages.length) {
      error.value = messages.join(" Â· ");
      return;
    }
  }

  if (err instanceof Error) {
    error.value = err.message;
    return;
  }

  if (typeof err === "string") {
    error.value = err;
    return;
  }

  error.value = "An unexpected error occurred during training.";
};

const updateTrainingJobs = (jobs: TrainingJob[]) => {
  const previous = new Map(trainingJobs.value.map((job) => [job.id, job.status]));
  trainingJobs.value = jobs.filter(
    (job) =>
      job.prediction_target === "knee_alignment" &&
      job.feature_schema_version === "fppa_v2",
  );
  const newlyCompleted = trainingJobs.value.some(
    (job) => job.status === "COMPLETED" && previous.get(job.id) !== "COMPLETED",
  );
  if (newlyCompleted) {
    invalidateModels();
  }
  selectedJob.value =
    trainingJobs.value.find((job) => job.id === selectedJob.value?.id) ??
    trainingJobs.value[0] ??
    null;
};

const refreshTrainingJobs = async () => {
  try {
    updateTrainingJobs(await trainingService.getTrainingJobs());
    error.value = null;
  } catch (err: unknown) {
    setErrorState(err);
  }
};

const fetchTrainingData = async (force = false) => {
  if (isInitialized.value && !force) {
    return;
  }

  isLoading.value = true;
  error.value = null;

  try {
    const [
      trainingJobsResponse,
      datasetsResponse,
      featureOptions,
      algorithmOptions,
    ] = await Promise.all([
      trainingService.getTrainingJobs(),
      datasetService.getDatasets(),
      Promise.resolve(trainingService.getAvailableFeatures()),
      Promise.resolve(trainingService.getAvailableAlgorithms()),
    ]);

    updateTrainingJobs(trainingJobsResponse);
    datasets.value = datasetsResponse;
    features.value = featureOptions;
    algorithms.value = algorithmOptions;

    if (
      !algorithmOptions.some(
        (algorithm) => algorithm.id === selectedAlgorithmId.value,
      )
    ) {
      selectedAlgorithmId.value = algorithmOptions[0]?.id ?? "xgboost";
    }

    isInitialized.value = true;
  } catch (err: unknown) {
    console.error("Training initialization error:", err);
    setErrorState(err);
    isInitialized.value = false;
  } finally {
    isLoading.value = false;
  }
};

const availableDatasets = computed(() =>
  datasets.value.filter(
    (dataset) =>
      dataset.status === "READY" &&
      dataset.purpose === "training" &&
      dataset.is_usable_for_training === true,
  ),
);

const filteredDatasets = computed(() => {
  if (!selectedViewAngle.value) {
    return [];
  }

  return availableDatasets.value.filter((dataset) => {
    const angle = selectedViewAngle.value!;
    const stats = dataset.angle_training_stats?.[angle];
    if (!(dataset.view_angles ?? []).includes(angle)) return false;

    return (stats?.knee_target_sample_count ?? 0) > 0;
  });
});

const selectedDatasets = computed(() =>
  datasets.value.filter((dataset) =>
    selectedDatasetIds.value.includes(dataset.id),
  ),
);

const selectedAlgorithm = computed(
  () =>
    algorithms.value.find(
      (algorithm) => algorithm.id === selectedAlgorithmId.value,
    ) ?? null,
);

const selectedFeatures = computed(() =>
  features.value.filter((feature) => feature.selected),
);

const selectedFeaturesCount = computed(() => selectedFeatures.value.length);

const activeJobs = computed(() =>
  trainingJobs.value.filter(
    (job) => job.status === "PENDING" || job.status === "RUNNING",
  ),
);

const isTraining = computed(() => isSubmitting.value || activeJobs.value.length > 0);

const completedJobs = computed(() =>
  trainingJobs.value.filter((job) => job.status === "COMPLETED"),
);

const bestF1Score = computed(() => {
  const scores = completedJobs.value
    .map((job) => {
      const value = job.metrics?.f1;
      return typeof value === "number" ? value : null;
    })
    .filter((value): value is number => value !== null);

  if (!scores.length) {
    return "--";
  }

  return `${(Math.max(...scores) * 100).toFixed(1)}%`;
});

const canStartTraining = computed(
  () =>
    selectedDatasetIds.value.length > 0 &&
    selectedViewAngle.value !== null &&
    selectedFeaturesCount.value > 0 &&
    selectedAlgorithm.value !== null &&
    !isTraining.value,
);

const summaryCards = computed(() => [
  {
    label: "Total Runs",
    value: trainingJobs.value.length,
    description: "FPPA v2 knee-alignment experiments",
    icon: "R",
    variant: "samples" as const,
  },
  {
    label: "Completed Runs",
    value: completedJobs.value.length,
    description: "Completed FPPA M1 runs",
    icon: "C",
    variant: "correct" as const,
  },
  {
    label: "Active Jobs",
    value: activeJobs.value.length,
    description: "Pending or running jobs",
    icon: "T",
    variant: "samples" as const,
  },
  {
    label: "Failed Runs",
    value: trainingJobs.value.filter((j) => j.status === "FAILED").length,
    description: "Experiments that ended with errors",
    icon: "F",
    variant: "incorrect" as const,
  },
]);

const configSummaryText = computed(() => {
  const datasetPart = selectedDatasetIds.value.length
    ? `${selectedDatasetIds.value.length} dataset(s)`
    : "No datasets";

  return `${datasetPart} Â· frontal view Â· FPPA knee alignment Â· six fixed FPPA features Â· XGBoost M1`;
});

const toggleDataset = (datasetId: number) => {
  const index = selectedDatasetIds.value.indexOf(datasetId);

  if (index >= 0) {
    selectedDatasetIds.value.splice(index, 1);
    return;
  }

  selectedDatasetIds.value.push(datasetId);
};

const setHyperparameter = (name: string, value: unknown) => {
  hyperparameters.value[name] = value;
};

const setTestSize = (value: number) => {
  testSize.value = value;
};

const setRandomSeed = (value: number) => {
  randomSeed.value = value;
};

const startTraining = async () => {
  if (!canStartTraining.value || !selectedAlgorithm.value) {
    return null;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const job = await trainingService.startTraining({
      dataset_ids: selectedDatasetIds.value,
      algorithm: selectedAlgorithm.value.id,
      view_angle: selectedViewAngle.value!,
      prediction_target: "knee_alignment",
      feature_selection: selectedFeatures.value.map((feature) => feature.id),
      hyperparameters: hyperparameters.value,
      test_size: testSize.value,
      random_seed: randomSeed.value,
    });

    trainingJobs.value.unshift(job);
    selectedJob.value = job;

    if (job.status === "COMPLETED") {
      invalidateModels();
    }

    return job;
  } catch (err: unknown) {
    console.error("Training start error:", err);

    const responseData = responseDataFor(err);
    if (
      typeof responseData === "object" &&
      responseData !== null &&
      "id" in responseData &&
      typeof (responseData as { id?: unknown }).id === "number" &&
      "status" in responseData &&
      typeof (responseData as { status?: unknown }).status === "string"
    ) {
      const failedJob = responseData as TrainingJob;
      trainingJobs.value = [
        failedJob,
        ...trainingJobs.value.filter((job) => job.id !== failedJob.id),
      ];
    }

    setErrorState(err);
    return null;
  } finally {
    isSubmitting.value = false;
  }
};

export function useTraining() {
  let pollTimer: ReturnType<typeof setTimeout> | undefined;
  let mounted = false;
  const poll = async () => {
    if (!mounted) return;
    if (activeJobs.value.length) await refreshTrainingJobs();
    if (mounted) pollTimer = setTimeout(poll, 3000);
  };
  onMounted(async () => {
    mounted = true;
    await fetchTrainingData(true);
    if (mounted) pollTimer = setTimeout(poll, 3000);
  });
  onUnmounted(() => {
    mounted = false;
    clearTimeout(pollTimer);
  });

  return {
    trainingJobs,
    datasets,
    features,
    algorithms,
    selectedDatasetIds,
    selectedDatasets,
    selectedViewAngle,
    selectedAlgorithm,
    selectedAlgorithmId,
    selectedFeatures,
    selectedFeaturesCount,
    hyperparameters,
    testSize,
    randomSeed,
    availableDatasets,
    filteredDatasets,
    activeJobs,
    completedJobs,
    summaryCards,
    configSummaryText,
    bestF1Score,
    isLoading,
    isTraining,
    isInitialized,
    error,
    selectedJob,
    selectJob,
    canStartTraining,
    fetchTrainingData,
    refreshTrainingJobs,
    toggleDataset,
    setHyperparameter,
    setTestSize,
    setRandomSeed,
    startTraining,
  };
}
```
### vectofit_admin/src/services/accountService.ts
```ts
import client from "../config/client";

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  is_annotator: boolean;
}

export const accountService = {
  async getCurrentUser(): Promise<CurrentUser> {
    const response = await client.get<CurrentUser>("/accounts/me/");
    return response.data;
  },

  async register(payload: {
    username: string;
    email: string;
    password: string;
    confirm_password: string;
    is_annotator: boolean;
  }): Promise<void> {
    await client.post("/accounts/register/", payload);
  },
};
```
### vectofit_admin/src/services/annotationPoolService.ts
```ts
import type { KneeAnnotation } from "./datasetAnnotationService";
import client from "../config/client";

export type AnnotationJobStatus =
  | "NO_SAMPLES"
  | "QUEUED"
  | "IN_PROGRESS"
  | "COMPLETED";

export interface AnnotationPoolAnnotator {
  id: number | null;
  username: string;
}

export interface AnnotationPoolAnnotatorSummary {
  annotator: AnnotationPoolAnnotator | null;
  activity_count: number;
  last_activity_at: string;
}

export interface AnnotationPoolActivity {
  id: number;
  sample_id: number;
  annotator: AnnotationPoolAnnotator | null;
  created_at: string;
  has_annotation: boolean;
  annotation: KneeAnnotation | null;
  rubric_version: string;
}

export interface AnnotationPoolJob {
  id: number;
  name: string;
  dataset_status: string;
  job_status: AnnotationJobStatus;
  sample_count: number;
  reviewed_count: number;
  pending_count: number;
  activity_count: number;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
  annotators: AnnotationPoolAnnotatorSummary[];
  activity: AnnotationPoolActivity[];
}

export const annotationPoolService = {
  async getJobs(): Promise<AnnotationPoolJob[]> {
    const response = await client.get<AnnotationPoolJob[]>(
      "/datasets/annotation-pool/",
    );
    return response.data;
  },
};
```
### vectofit_admin/src/services/datasetAnnotationService.ts
```ts
import client from "../config/client";
import { initializeCsrf, publicClient } from "../config/publicAuth";
const isPublic = import.meta.env.MODE === "public";

export type KneeAlignmentGrade =
  | "aligned"
  | "borderline"
  | "deviated"
  | "unassessable";

export type KneeDeviationDirection = "valgus" | "varus" | "none" | "uncertain";

export type SymmetryObservation =
  | "symmetric"
  | "asymmetric"
  | "uncertain"
  | "not_recorded";

export type TargetLabel = "good" | "bad" | "borderline" | "unassessable";

export interface KneeSideAnnotation {
  grade: KneeAlignmentGrade | null;
  direction: KneeDeviationDirection | null;
}

export interface KneeAnnotation {
  left: KneeSideAnnotation;
  right: KneeSideAnnotation;
  symmetry_observation: SymmetryObservation;
  notes: string;
}

export interface RepAssessment {
  id: number;
  rep_number: number;
  start_frame: number | null;
  end_frame: number | null;
  classification: string;
}

export interface DatasetVideoPlayback {
  id: number;
  video_url: string | null;
  participant_code: string;
  view_angle_name: string;
  source_label?: boolean | null;
  source_path?: string;
  requires_manual_review?: boolean;
}

export interface DatasetSample {
  id: number;
  dataset: number;
  dataset_video: DatasetVideoPlayback | number | null;
  video_fps?: number | null;
  is_manually_annotated?: boolean;
  rep_assessment: RepAssessment;

  is_correct: boolean | null;
  error_label: string;
  annotator: number | null;
  annotated_at: string | null;
  created_at: string;

  knee_annotation?: KneeAnnotation | null;
  target_label?: TargetLabel | null;
}

export interface AnnotationSession {
  dataset: {
    id: number;
    name: string;
    exercise_type: string;
    view_angle: number | null;
    video_url: string | null;
    sample_count: number;
    labelled_sample_count: number;
    is_usable_for_training: boolean;
    status: string;
  };
  fps: number;
  samples: DatasetSample[];
}

export interface DatasetSamplePlaybackFields {
  dataset_video: DatasetVideoPlayback | null;
  video_fps: number | null;
}

export interface SaveAnnotationPayload {
  knee_annotation: KneeAnnotation;
}

export const emptyKneeAnnotation = (): KneeAnnotation => ({
  left: { grade: null, direction: null },
  right: { grade: null, direction: null },
  symmetry_observation: "not_recorded",
  notes: "",
});

export const datasetAnnotationService = {
  async getSession(datasetId: number): Promise<AnnotationSession> {
    const response = await client.get<AnnotationSession>(
      isPublic ? `/annotator/datasets/${datasetId}/session/` : `/datasets/${datasetId}/annotation/`,
    );
    return response.data;
  },

  async save(
    sampleId: number,
    payload: SaveAnnotationPayload,
  ): Promise<DatasetSample> {
    if (isPublic) {
      await initializeCsrf();
      const { data } = await publicClient.patch<DatasetSample>(`samples/${sampleId}/rating/`, payload);
      return data;
    }
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      payload,
    );
    return response.data;
  },

  async clear(sampleId: number): Promise<DatasetSample> {
    if (isPublic) {
      await initializeCsrf();
      const { data } = await publicClient.patch<DatasetSample>(`samples/${sampleId}/rating/`, { knee_annotation: null });
      return data;
    }
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      { knee_annotation: null },
    );
    return response.data;
  },
};
```
### vectofit_admin/src/services/datasetService.ts
```ts
import client from "../config/client";

export interface CreateDatasetPayload {
  name: string;
  description?: string;
  participant: number | null;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  view_angle?: number | null;
  video_file: File | null;
}

export interface Participant {
  id: number;
  participant_code: string;
  created_at: string;
}

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

export const VIEW_ANGLE_BY_ID: Record<number, ViewAngle> = {
  1: "diagonal",
  2: "frontal",
  3: "sagittal",
};

export interface AngleTrainingStats {
  sample_count: number;
  labelled_sample_count: number;
  good_count: number;
  bad_count: number;
  error_type_sample_count: number;
  error_label_counts: Record<string, number>;
  knee_target_sample_count: number;
  knee_label_counts: Record<
    "good" | "bad" | "borderline" | "unassessable" | "disputed" | "missing",
    number
  >;
  participant_count: number;
  video_count: number;
}

export interface Dataset {
  id: number;
  name: string;
  description: string;
  participant: number | null;
  view_angle: number | null;

  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target: string;

  created_at: string;
  updated_at: string;

  sample_count: number;
  labelled_sample_count: number;
  is_usable_for_training: boolean;

  status: DatasetStatus;
  error_message: string | null;

  video_file: string | null;
  video_url: string | null;
  video_count?: number;
  ready_video_count?: number;
  failed_video_count?: number;

  participant_count?: number;
  view_angles?: ViewAngle[];
  angle_training_stats?: Partial<Record<ViewAngle, AngleTrainingStats>>;

  review_policy?: "source_labels" | "all_videos" | "subset";
  review_selected_sample_count?: number;
  human_reviewed_sample_count?: number;
  pending_review_sample_count?: number;
  inherited_labelled_sample_count?: number;
}

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
  expires_at: number;
  manifest: DatasetImportManifest;
}

export interface DatasetImportManifest {
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isViewAngle(value: unknown): value is ViewAngle {
  return value === "diagonal" || value === "frontal" || value === "sagittal";
}

function isDatasetImportPreview(value: unknown): value is DatasetImportPreview {
  if (!isRecord(value)) {
    return false;
  }

  if (
    !(typeof value.upload_token === "string" || value.upload_token === null) ||
    !isNumber(value.expires_at) ||
    !isRecord(value.manifest)
  ) {
    return false;
  }

  const manifest = value.manifest;

  if (
    !isNumber(manifest.file_count) ||
    !isNumber(manifest.participant_count) ||
    !isNumber(manifest.ignored_file_count) ||
    !isRecord(manifest.by_label) ||
    !isRecord(manifest.by_angle)
  ) {
    return false;
  }

  const byLabel = manifest.by_label;
  const byAngle = manifest.by_angle;

  if (
    !isNumber(byLabel.good) ||
    !isNumber(byLabel.bad) ||
    !isNumber(byAngle.diagonal) ||
    !isNumber(byAngle.frontal) ||
    !isNumber(byAngle.sagittal)
  ) {
    return false;
  }

  if (
    !Array.isArray(manifest.files) ||
    !manifest.files.every(
      (file: unknown) =>
        isRecord(file) &&
        typeof file.archive_path === "string" &&
        typeof file.filename === "string" &&
        typeof file.participant_code === "string" &&
        isViewAngle(file.view_angle) &&
        typeof file.source_label == "boolean" &&
        isNumber(file.size_bytes),
    )
  ) {
    return false;
  }

  if (
    !Array.isArray(manifest.warnings) ||
    !manifest.warnings.every(
      (warning: unknown) => typeof warning === "string",
    ) ||
    !Array.isArray(manifest.errors) ||
    !manifest.errors.every((error: unknown) => typeof error === "string")
  ) {
    return false;
  }

  return true;
}

export type DatasetReviewPolicy = "source" | "all" | "subset";

export type DatasetSelectionMethod = "stratified" | "manual";

export interface DatasetBulkImportPayload {
  upload_token: string | null;
  name: string;
  description?: string;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  review_policy: DatasetReviewPolicy;
  selection_method: DatasetSelectionMethod;
  review_count?: number;
  random_seed?: number;
  selected_video_paths?: string[];
  files?: DatasetImportFile[];
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

export type DatasetStatus =
  | "PENDING"
  | "PROCESSING"
  | "READY"
  | "FAILED"
  | "PARTIAL";

export const datasetService = {
  async getDatasets(): Promise<Dataset[]> {
    const response = await client.get<Dataset[]>("/datasets/");
    return response.data;
  },

  async getDataset(id: number): Promise<Dataset> {
    const response = await client.get<Dataset>(`/datasets/${id}/`);
    return response.data;
  },

  async getParticipants(): Promise<Participant[]> {
    const response = await client.get<Participant[]>("/datasets/participant/");
    return response.data;
  },

  async createDatasetWithVideo(payload: FormData): Promise<Dataset> {
    const response = await client.post<Dataset>("/datasets/", payload);
    return response.data;
  },

  async retryDataset(id: number): Promise<Dataset> {
    const response = await client.post<Dataset>(`/datasets/${id}/retry/`);

    return response.data;
  },

  async previewDatasetArchive(file: File): Promise<DatasetImportPreview> {
    const formData = new FormData();
    formData.append("zip_file", file);

    const response = await client.post<DatasetImportPreview>(
      "/datasets/import/preview/",
      formData,
    );

    if (!isDatasetImportPreview(response.data)) {
      throw new Error(
        "The server returned an invalid archive preview response.",
      );
    }

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
};
```
### vectofit_admin/src/services/modelService.ts
```ts
import client from "../config/client";

export type DeploymentStatus = "active" | "building" | "failed" | "inactive";

export type PredictionTarget = "binary_form" | "error_type" | "knee_alignment";

export type ModelCardCheckStatus = "pass" | "warn" | "fail";

export interface ModelCardCheck {
  code: string;
  label: string;
  status: ModelCardCheckStatus;
  detail: string;
  remediation: string | null;
}

export interface ModelCard {
  schema_version: string;
  status: "ready" | "warning" | "blocked";
  generated_from: {
    job_id: number;
    registry_entry_id: number;
    manifest_version: number | null;
    manifest_sha256: string | null;
  };
  activation: {
    allowed: boolean;
    blockers: ModelCardCheck[];
    warnings: ModelCardCheck[];
  };
  checks: ModelCardCheck[];
  summary: {
    total_checks: number;
    passed_checks: number;
    warning_checks: number;
    failed_checks: number;
  };
  class_mapping: Record<string, string>;
  target_names: string[];
  prediction_target: PredictionTarget;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  feature_schema_version: string;
  evaluation_scope: string;
  held_out_test_count: number;
  data_provenance: {
    participant_count: number;
    label_origin_counts: Record<string, number>;
    split_counts: Record<string, number>;
  };
}

export interface PerClassMetric {
  index: number;
  label: string;
  support: number;
  predicted_count: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export interface ModelRegistryRecord {
  id: number;
  name: string;
  version: string;
  training_job: number;
  algorithm: string;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  metrics: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface ModelState {
  id: number;
  name: string;
  version: string;
  algorithm: string;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  is_active: boolean;
  created_at: string;
  artifact_available: boolean;

  training: {
    job_id: number;
    status: string;
    view_angle: "diagonal" | "frontal" | "sagittal" | "";
    prediction_target: PredictionTarget;
    feature_schema_version: string;
    test_size: number;
    dataset_names: string[];
    sample_count: number;
    train_count: number;
    test_count: number;
    split_strategy: string;
    random_seed: number;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
  };

  features: {
    selected: string[];
    importances: Record<string, number>;
  };

  evaluation: {
    accuracy: number | null;
    balanced_accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1: number | null;
    confusion_matrix: number[][];
    class_mapping: Record<string, string>;
    target_names: string[];
    per_class: PerClassMetric[];
    overall_class_distribution: Record<string, number>;
    train_class_distribution: Record<string, number>;
    test_class_distribution: Record<string, number>;
    evaluation_scope: string;
    test_count: number;
  };

  feature_warnings: string[];
  training_manifest: Record<string, unknown>;
  model_card: ModelCard;
}

export const modelService = {
  async getModels(): Promise<ModelRegistryRecord[]> {
    const response =
      await client.get<ModelRegistryRecord[]>("/training/models/");

    return response.data;
  },

  async activateModel(id: number): Promise<ModelRegistryRecord> {
    const response = await client.post<ModelRegistryRecord>(
      `/training/models/${id}/activate/`,
    );
    return response.data;
  },

  async getModelState(id: number): Promise<ModelState> {
    const response = await client.get<ModelState>(
      `/training/models/${id}/state/`,
    );

    return response.data;
  },
};
```
### vectofit_admin/src/services/participantService.ts
```ts
import client from "../config/client";

export interface Participant {
  id: number;
  participant_code: string;
  created_at: string;
}

export const participantService = {
  async getParticipants(): Promise<Participant[]> {
    const response = await client.get<Participant[]>("/datasets/participant/");

    return response.data;
  },

  async createParticipant(): Promise<Participant> {
    const response = await client.post<Participant>(
      "/datasets/participant/",
      {},
    );

    return response.data;
  },

  async getParticipant(id: number): Promise<Participant> {
    const response = await client.get<Participant>(
      `/datasets/participant/${id}/`,
    );

    return response.data;
  },

  async deleteParticipant(id: number): Promise<void> {
    await client.delete(`/datasets/participant/${id}/`);
  },
};
```
### vectofit_admin/src/services/pilotResultsService.ts
```ts
import client from "../config/client";

export interface PilotParticipantResult {
  participant: string;
  macro_f1: number;
  sample_count: number;
}

export interface PilotMetricResult {
  macro_f1: number;
  confusion_matrix: number[][];
  per_participant: PilotParticipantResult[];
  oof_predictions?: Array<{
    participant: string;
    label: number;
    prediction: number;
  }>;
}

export interface PilotResults {
  label: string;
  feature_schema_version: string;
  M0_features: string[];
  M1_features: string[];
  M0: PilotMetricResult;
  M1: PilotMetricResult;
  delta_macro_f1: number;
  delta_macro_f1_bootstrap_95: {
    lower: number;
    upper: number;
  };
  threshold_rule_baseline: {
    rule: string;
    primary: PilotMetricResult & {
      label: string;
      cutoff_degrees: { valgus: number; varus: number };
    };
    sensitivity: Array<
      PilotMetricResult & {
        label: string;
        cutoff_degrees: { valgus: number; varus: number };
      }
    >;
  };
}

export const pilotResultsService = {
  async getResults(): Promise<PilotResults> {
    const response = await client.get<PilotResults>("/training/pilot-results/");
    return response.data;
  },
};
```
### vectofit_admin/src/services/trainingService.ts
```ts
import client from "../config/client";
import type { ViewAngle } from "./datasetService";

export type PredictionTarget = "binary_form" | "error_type" | "knee_alignment";

export type TrainingJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface TrainingJob {
  id: number;
  dataset_ids: number[];
  dataset_names: string[];
  algorithm: string;
  view_angle: ViewAngle | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  training_manifest_summary?: Record<string, unknown>;
  feature_selection: string[];
  hyperparameters: Record<string, unknown>;
  random_seed: number;
  test_size: number;
  split_strategy: string;
  status: TrainingJobStatus;
  error_message: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  sample_count: number;
  train_count: number;
  test_count: number;
  metrics: Record<string, unknown>;
  feature_warnings: string[];
  has_artifact: boolean;
  artifact_url: string | null;
}

export interface FeatureOption {
  id:
    | "fppa_l_bottom"
    | "fppa_r_bottom"
    | "fppa_l_peak"
    | "fppa_r_peak"
    | "asym_bottom"
    | "asym_peak";
  name: string;
  selected: boolean;
}

export interface AlgorithmOption {
  id: "xgboost";
  code: string;
  name: string;
  description: string;
}

export interface SplitStrategyOption {
  id: string;
  name: string;
  description: string;
}

export interface WorkflowStep {
  number: string;
  title: string;
  subtitle: string;
  active?: boolean;
}

export type Hyperparameters = Record<string, unknown>;

export const trainingService = {
  async getTrainingJobs(): Promise<TrainingJob[]> {
    const response = await client.get<TrainingJob[]>("/training/jobs/");
    return response.data;
  },

  async startTraining(payload: {
    dataset_ids: number[];
    algorithm: string;
    view_angle: ViewAngle;
    prediction_target: PredictionTarget;
    feature_selection: string[];
    hyperparameters: Record<string, unknown>;
    test_size: number;
    random_seed: number;
  }): Promise<TrainingJob> {
    const response = await client.post<TrainingJob>(
      "/training/jobs/create/",
      payload,
    );

    return response.data;
  },

  getAvailableFeatures(): FeatureOption[] {
    return [
      {
        id: "fppa_l_bottom",
        name: "Left FPPA at squat bottom",
        selected: true,
      },
      {
        id: "fppa_r_bottom",
        name: "Right FPPA at squat bottom",
        selected: true,
      },
      {
        id: "fppa_l_peak",
        name: "Left peak FPPA",
        selected: true,
      },
      {
        id: "fppa_r_peak",
        name: "Right peak FPPA",
        selected: true,
      },
      {
        id: "asym_bottom",
        name: "Bottom bilateral asymmetry",
        selected: true,
      },
      {
        id: "asym_peak",
        name: "Peak bilateral asymmetry",
        selected: true,
      },
    ];
  },

  getAvailableAlgorithms(): AlgorithmOption[] {
    return [
      {
        id: "xgboost",
        code: "xgb",
        name: "XGBoost M1",
        description:
          "Predicts human-reviewed good/bad knee-alignment labels from FPPA v2 features.",
      },
    ];
  },

  getSplitStrategy(): SplitStrategyOption[] {
    return [
      {
        id: "group_by_participant",
        name: "Group by Participant",
        description:
          "Keeps repetitions from the same participant in a single split to prevent subject-level leakage.",
      },
    ];
  },

};
```

## Approved scope update (2026-11-06)
User authorized private auth guards and a consistent token condition for admin and annotator. Both private role trees require a persisted token validated by accounts/me, with role-appropriate routing. Both private sign-outs clear the token. Public mode retains its existing cookie/CSRF guard. These are intentional differences from the Vue reference. The Phase 0 stop condition is resolved.

