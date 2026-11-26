import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useInferenceLab } from "../../hooks/useInferenceLab";
import {
  inferenceService,
  type InferenceRun,
} from "../../services/inferenceService";
import styles from "./InferenceLab.module.css";

function formatNumber(value: number | null | undefined, suffix: string) {
  if (typeof value !== "number" || !Number.isFinite(value))
    return "Unavailable";
  return `${value.toFixed(1)}${suffix}`;
}

function predictionLabel(value?: string) {
  if (value === "good") return "Good knee alignment";
  if (value === "bad") return "Needs improvement";
  return value ?? "Unavailable";
}

function RunReport({ run, total }: { run: InferenceRun; total: number }) {
  const assessed = run.predictions.filter(
    (item) => item.status === "assessed",
  ).length;
  const average =
    assessed && run.inference_ms !== null ? run.inference_ms / assessed : null;
  return (
    <article className={styles.run}>
      <h3>
        {run.model_snapshot.name} v{run.model_snapshot.version}
        <span>{run.status.toLowerCase()}</span>
      </h3>
      {run.error_message && (
        <p role="alert" className={styles.error}>
          {run.error_message}
        </p>
      )}
      {run.status === "COMPLETED" && (
        <>
          <p className={styles.help}>
            Assessed: {assessed}/{total} ? Loading:{" "}
            {formatNumber(run.model_loading_ms, " ms")}
            {" ? "}Total inference: {formatNumber(run.inference_ms, " ms")}
            {" ? "}Average per assessed rep: {formatNumber(average, " ms")}
          </p>
          <div className={styles.tableScroll}>
            <table>
              <thead>
                <tr>
                  <th>Rep</th>
                  <th>Knee-alignment prediction</th>
                  <th>Confidence</th>
                  <th>Inference latency</th>
                </tr>
              </thead>
              <tbody>
                {run.predictions.map((item) => (
                  <tr key={item.rep_number}>
                    <td>{item.rep_number}</td>
                    <td>
                      {item.status === "assessed"
                        ? predictionLabel(item.predicted_class)
                        : `Unavailable: ${item.reason?.replaceAll("_", " ") ?? "invalid features"}`}
                    </td>
                    <td>
                      {formatNumber(
                        item.probability == null
                          ? null
                          : item.probability * 100,
                        "%",
                      )}
                    </td>
                    <td>{formatNumber(item.inference_ms, " ms")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </article>
  );
}

export default function InferenceLab() {
  const lab = useInferenceLab();
  const fileInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const simulationId = lab.simulationId;
  const file = lab.file;

  useEffect(() => {
    let url: string | null = null;
    const controller = new AbortController();
    setPreview(null);
    setPreviewError(null);
    if (file) {
      url = URL.createObjectURL(file);
      setPreview(url);
    } else if (simulationId !== null) {
      inferenceService
        .getVideo(simulationId, controller.signal)
        .then((blob) => {
          if (controller.signal.aborted) return;
          url = URL.createObjectURL(blob);
          setPreview(url);
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setPreviewError("The saved video could not be loaded.");
        });
    }
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [file, simulationId]);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFileError(null);
    if (selected && selected.size > 200 * 1024 * 1024) {
      setFileError("Choose a video of 200 MB or smaller.");
      lab.setFile(null);
      event.target.value = "";
      return;
    }
    lab.setFile(selected);
  }

  function selectSimulation(id: number | null) {
    lab.selectSimulation(id);
    setFileError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function deleteSimulation() {
    if (
      window.confirm(
        `Delete ${lab.simulation?.original_filename} and all its results?`,
      )
    )
      lab.remove();
  }

  const simulation = lab.simulation;
  return (
    <main className={styles.page}>
      <header className={styles.heading}>
        <div>
          <h1>Inference Lab</h1>
          <p>
            Run trained knee-alignment models on the same frontal squat video.
          </p>
        </div>
        <button
          type="button"
          onClick={() => selectSimulation(null)}
          disabled={lab.pending}
        >
          New simulation
        </button>
      </header>
      {lab.error && (
        <p className={styles.error} role="alert">
          {lab.error}
        </p>
      )}
      <div className={styles.workspace}>
        <section className={styles.panel} aria-labelledby="simulation-title">
          <h2 id="simulation-title">Simulation</h2>
          <label className={styles.field}>
            Model
            <select
              value={lab.modelId ?? ""}
              onChange={(event) =>
                lab.setModelId(
                  event.target.value ? Number(event.target.value) : null,
                )
              }
              disabled={lab.pending}
            >
              <option value="">
                {lab.isLoadingModels ? "Loading models..." : "Select a model"}
              </option>
              {lab.models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} v{model.version}
                  {model.is_active ? " (active)" : " (inactive)"}
                </option>
              ))}
            </select>
          </label>
          {!lab.isLoadingModels && !lab.models.length && (
            <p>
              No compatible frontal FPPA v2 models are available. Complete
              training first.
            </p>
          )}
          {lab.model.isFetching && (
            <p role="status">Checking model availability...</p>
          )}
          {lab.model.data &&
            (!lab.model.data.artifact_available ||
              lab.model.data.training.status !== "COMPLETED") && (
              <p role="status">
                This model has no completed, available artifact. Choose another
                model.
              </p>
            )}
          {lab.model.data && (
            <p className={styles.help}>
              Inputs: {lab.model.data.features.selected.join(", ")}
            </p>
          )}
          {simulationId === null ? (
            <label className={styles.field}>
              Frontal squat video
              <input
                ref={fileInput}
                type="file"
                accept="video/*"
                disabled={lab.pending}
                onChange={selectFile}
              />
            </label>
          ) : (
            <p className={styles.filename}>
              {simulation?.original_filename ?? "Loading simulation..."}
            </p>
          )}
          <p className={styles.help}>
            Frontal view only. Maximum 200 MB and five minutes. Predictions
            assess knee alignment; asymmetry values are measurements.
          </p>
          {fileError && (
            <p role="alert" className={styles.error}>
              {fileError}
            </p>
          )}
          {preview ? (
            <video
              className={styles.video}
              src={preview}
              controls
              preload="metadata"
              aria-label="Simulation video"
              onError={() =>
                setPreviewError(
                  "Your browser cannot preview this video. Server processing may still support it.",
                )
              }
            />
          ) : (
            <p className={styles.placeholder}>
              {previewError
                ? "Video preview unavailable."
                : simulationId !== null
                  ? "Loading saved video..."
                  : "Choose a video to preview it here."}
            </p>
          )}
          {previewError && (
            <p role="alert" className={styles.error}>
              {previewError}
            </p>
          )}
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.primary}
              disabled={!lab.canRun}
              onClick={lab.start}
            >
              {lab.pending
                ? "Submitting..."
                : lab.active
                  ? "Processing..."
                  : lab.existingRun?.status === "FAILED"
                    ? "Retry inference"
                    : "Run inference"}
            </button>
            {simulation && (
              <button
                type="button"
                disabled={lab.active || lab.pending}
                onClick={deleteSimulation}
              >
                Delete simulation
              </button>
            )}
          </div>
          {lab.existingRun?.status === "COMPLETED" && (
            <p className={styles.help}>
              This model already has saved results for this video. Select
              another model to compare.
            </p>
          )}
          {simulation && (
            <p role="status">
              Video preparation: {simulation.status.toLowerCase()}
              {simulation.preprocessing_ms !== null
                ? ` ? ${formatNumber(simulation.preprocessing_ms / 1000, " s")}`
                : ""}
            </p>
          )}
          {simulation?.error_message && (
            <p role="alert" className={styles.error}>
              {simulation.error_message}
            </p>
          )}
        </section>
        <aside className={styles.panel} aria-labelledby="history-title">
          <h2 id="history-title">Saved history</h2>
          {lab.history.isPending && <p role="status">Loading history...</p>}
          {!lab.history.isPending && !lab.history.data?.results.length && (
            <p>No saved simulations yet.</p>
          )}
          <ul className={styles.history}>
            {lab.history.data?.results.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  aria-pressed={simulationId === item.id}
                  disabled={lab.pending}
                  onClick={() => selectSimulation(item.id)}
                >
                  <strong>{item.original_filename}</strong>
                  <span>
                    {new Date(item.created_at).toLocaleString()} ? preparation{" "}
                    {item.status.toLowerCase()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <div className={styles.actions}>
            <button
              type="button"
              disabled={!lab.history.data?.previous || lab.history.isFetching}
              onClick={() => lab.setPage(lab.page - 1)}
            >
              Previous
            </button>
            <span>Page {lab.page}</span>
            <button
              type="button"
              disabled={!lab.history.data?.next || lab.history.isFetching}
              onClick={() => lab.setPage(lab.page + 1)}
            >
              Next
            </button>
          </div>
        </aside>
      </div>
      {simulationId !== null && lab.detail.isPending && (
        <p role="status">Loading results...</p>
      )}
      {simulation && (
        <section className={styles.panel} aria-labelledby="comparison-title">
          <h2 id="comparison-title">Model comparison</h2>
          <p className={styles.help}>
            All models use the same saved repetitions. Confidence is the model
            probability, not measured accuracy. Latency excludes upload,
            queueing, video preparation, and model loading.
          </p>
          {simulation.runs.map((run) => (
            <RunReport
              key={run.id}
              run={run}
              total={simulation.repetitions.length}
            />
          ))}
          {simulation.repetitions.length > 0 && (
            <>
              <h3>Measured bilateral asymmetry</h3>
              <p className={styles.help}>
                Absolute left?right FPPA difference in degrees. These
                measurements are shared across all model runs.
              </p>
              <div className={styles.tableScroll}>
                <table>
                  <thead>
                    <tr>
                      <th>Rep</th>
                      <th>Video interval</th>
                      <th>At bottom</th>
                      <th>At peak</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulation.repetitions.map((rep) => (
                      <tr key={rep.rep_number}>
                        <td>{rep.rep_number}</td>
                        <td>
                          {formatNumber(rep.start_ms / 1000, " s")}?
                          {formatNumber(rep.end_ms / 1000, " s")}
                        </td>
                        <td>
                          {formatNumber(
                            rep.valid ? rep.features.asym_bottom : null,
                            "?",
                          )}
                        </td>
                        <td>
                          {formatNumber(
                            rep.valid ? rep.features.asym_peak : null,
                            "?",
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
