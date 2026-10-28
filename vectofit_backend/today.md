Understood. I’ll keep responses tight and move proactively.

## VectoFit operation map

### OP-01: Harden Dataset Processing

**Goal:** Dataset processing must be fully controllable from Admin UI.

**Backend**

- `apps/datasets/services/tasks.py`
  - Make processing atomic.
  - Clean up prior partial session/sample state before retry.
  - Guarantee `PENDING → PROCESSING → READY/FAILED`.
  - Store useful failure messages.
- `apps/datasets/views.py`
  - Remove dead `_process_dataset_video()`.
  - Add admin action: `POST /datasets/<id>/retry/`.
- `apps/datasets/urls.py`
  - Expose retry endpoint.
- `apps/datasets/serializers.py`
  - Ensure processing state + counts are exposed.

**Frontend**

- `src/services/datasetService.ts`
  - `retryDataset(id)`
- `src/hooks/useDatasets.ts`
  - Refresh/poll processing state.
- `src/pages/views/Datasets.vue`
  - `PROCESSING` → live state
  - `FAILED` → Retry
  - `READY` → Annotate
  - show sample/label counts.

**Acceptance**

```text
Upload → Processing → Ready
Upload → Processing → Failed → Retry → Ready
```

No shell intervention.

---

### OP-02: Admin Annotation

**Goal:** Label reps completely through UI.

- Dataset annotation route
- Video player
- Rep navigation
- Correct / Incorrect
- Error labels
- Save via existing `DatasetSample` PATCH
- Progress: `8/17 labelled`

No schema migration unless we hit an actual requirement.

---

### OP-03: Training Pipeline

**Goal:** One real training experiment from Admin UI.

- Fix/verify training API route mismatch.
- Ensure Dataset selection uses only `READY + labelled`.
- Preserve participant-group split.
- Run XGBoost.
- Persist artifact + metrics.
- Show training result in UI.

**Constraint:** We need at least **2 participants** for the current group-based held-out evaluation.

---

### OP-04: Evaluation

**Goal:** Make evaluation an actual experiment result, not a placeholder.

- Confusion matrix
- Accuracy
- Precision
- Recall
- F1
- Class distribution
- Dataset/participant split metadata
- Read-only result view

---

### OP-05: Model Registry + Deployment

**Goal:** Turn a completed training job into an actual deployable model.

- Align `Models.vue` with Django `ModelRegistry`.
- Add activate/deactivate model version.
- Deployment state.
- Rollback.
- Remove current mock deployment assumptions.

---

### OP-06: Inference API

**Goal:** Actual backend model inference.

```text
landmarks
   ↓
feature extraction
   ↓
active XGBoost model
   ↓
prediction
   ↓
VectoFit result
```

This is currently not complete. The classifier app is still effectively a stub. repomix-output(4)

---

### OP-07: Mobile Integration

Only after OP-06:

```text
Camera
→ MediaPipe
→ Rep segmentation
→ Feature extraction
→ Inference API / chosen inference path
→ Assessment result
```

---

## Today's execution order

```text
1. OP-01 Dataset lifecycle
2. OP-02 Annotation
3. Get Participant 2
4. OP-03 First real training
5. OP-04 Evaluation
6. OP-05 Registry/deployment
7. OP-06 Inference
8. OP-07 Mobile
```

### Immediate implementation target

**We should now modify OP-01, not manually repair Dataset #10.**

The first files to work on are:

```text
backend/
  apps/datasets/services/tasks.py
  apps/datasets/views.py
  apps/datasets/urls.py
  apps/datasets/serializers.py

admin/
  src/services/datasetService.ts
  src/hooks/useDatasets.ts
  src/pages/views/Datasets.vue
```

Your existing architecture already has most of the pieces. The main issue is that the **control flow isn't exposed cleanly through the Admin system yet**.

From here, I'll treat the Admin portal as the source of operational control, and shell commands only as diagnostics when something genuinely breaks.
