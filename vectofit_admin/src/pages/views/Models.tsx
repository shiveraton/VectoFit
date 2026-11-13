import { useModels } from "../../hooks/useModels";
import ModelCard from "../../components/models/ModelCard";
import ModelEvaluationState from "../../components/models/ModelEvaluationState";
import ModelFeatureState from "../../components/models/ModelFeatureState";
import ModelRegistryTable from "../../components/models/ModelRegistryTable";
import { bindStyles, each, display, scopeAttributes } from "../../presentation";
import styles from "./Models.module.css";
export default function Models(input: {}) {
  const cx = bindStyles(styles);
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
  const statusLabel = (() => {
    const model = modelState;
    if (!model) return "NO MODEL";
    return model.is_active ? "ACTIVE" : "REGISTERED";
  })();
  const canActivateModel = (() => {
    const model = modelState;
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
  })();
  const activationBlockers = (() =>
    modelState?.model_card?.activation.blockers ?? [])();
  const predictionTargetLabel = (() => {
    return modelState?.prediction_target === "knee_alignment"
      ? "Frontal-plane knee alignment"
      : "Unsupported model setup";
  })();
  const cameraAngleLabel = (() => {
    const angle = modelState?.view_angle;
    if (!angle) return "Unspecified";
    return angle.charAt(0).toUpperCase() + angle.slice(1);
  })();
  const selectedDatasetText = (() => {
    const datasetNames = modelState?.training.dataset_names ?? [];
    return datasetNames.length
      ? datasetNames.join(", ")
      : "No dataset recorded";
  })();
  const evaluationAvailable = (() => {
    const model = modelState;
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
  })();
  const formatDate = (value: string | null | undefined): string => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  };
  return (
    <>
      <div
        {...scopeAttributes(input)}
        data-v-models=""
        className={cx("models-page")}
      >
        <header data-v-models="" className={cx("page-header")}>
          <div data-v-models="" className={cx("page-heading")}>
            <div data-v-models="" className={cx("eyebrow")}>
              <span data-v-models="" className={cx("eyebrow-dot")}></span>
              {" VECTOFIT MODEL STATE "}
            </div>
            <h1 data-v-models="">{"Models"}</h1>
            <p data-v-models="">
              {
                " Inspect FPPA M1 provenance and held-out performance, then activate a validated version for frontal-plane knee-alignment inference. "
              }
            </p>
          </div>
        </header>
        {error ? (
          <div data-v-models="" role="alert" className={cx("error-banner")}>
            {display(error)}
          </div>
        ) : null}
        {activationMessage ? (
          <div
            data-v-models=""
            role="status"
            className={cx("activation-banner")}
          >
            {display(activationMessage)}
          </div>
        ) : null}
        {isLoading && models.length === 0 ? (
          <section
            data-v-models=""
            aria-live="polite"
            className={cx("content-card loading-card")}
          >
            {" Loading model registry… "}
          </section>
        ) : !isLoading && models.length === 0 ? (
          <section
            data-v-models=""
            className={cx("content-card empty-state-card")}
          >
            <h2 data-v-models="">{"No FPPA v2 models available"}</h2>
            <p data-v-models="">
              {
                " Complete a frontal knee-alignment M1 training run. FPPA v2 model versions will appear here after training and registration. "
              }
            </p>
          </section>
        ) : (
          <>
            {isStateLoading ? (
              <div
                data-v-models=""
                aria-live="polite"
                className={cx("state-loading")}
              >
                {" Loading selected model state… "}
              </div>
            ) : modelState ? (
              <>
                <section data-v-models="" className={cx("hero-card")}>
                  <div data-v-models="" className={cx("hero-information")}>
                    <div data-v-models="" className={cx("model-kicker")}>
                      {display(modelState.algorithm)}
                    </div>
                    <div data-v-models="" className={cx("model-title-row")}>
                      <h2 data-v-models="">{display(modelState.name)}</h2>
                      <span data-v-models="" className={cx("version-badge")}>
                        {" v"}
                        {display(modelState.version)}
                      </span>
                    </div>
                    <p data-v-models="" className={cx("model-caption")}>
                      {" Trained from job #"}
                      {display(modelState.training.job_id)}
                      {" · Created "}
                      {display(formatDate(modelState.created_at))}
                    </p>
                  </div>
                  <div data-v-models="" className={cx("hero-actions")}>
                    <span
                      data-v-models=""
                      className={cx("state-badge", {
                        active: modelState.is_active,
                      })}
                    >
                      {display(statusLabel)}
                    </span>
                    {!modelState.is_active && activationBlockers.length ? (
                      <span
                        data-v-models=""
                        className={cx("activation-blocked-note")}
                      >
                        {" Activation blocked "}
                      </span>
                    ) : null}
                    {canActivateModel ? (
                      <button
                        data-v-models=""
                        type="button"
                        disabled={isActivatingModel}
                        onClick={() => {
                          activateModel(modelState.id);
                        }}
                        className={cx("activate-button")}
                      >
                        {display(
                          isActivatingModel
                            ? "Activating…"
                            : "Activate for inference",
                        )}
                      </button>
                    ) : null}
                  </div>
                </section>
                <section
                  data-v-models=""
                  aria-label="Model summary"
                  className={cx("summary-grid")}
                >
                  {each(summaryCards).map(([_index, card]) => (
                    <div
                      data-v-models=""
                      key={card.label}
                      className={cx("summary-card")}
                    >
                      <span data-v-models="">{display(card.label)}</span>
                      <strong data-v-models="">{display(card.value)}</strong>
                      <small data-v-models="">
                        {display(card.description)}
                      </small>
                    </div>
                  ))}
                </section>
                {modelState.model_card ? (
                  <ModelCard
                    data-v-models=""
                    card={modelState.model_card}
                  ></ModelCard>
                ) : null}
                <section data-v-models="" className={cx("content-card")}>
                  <div data-v-models="" className={cx("section-header")}>
                    <div data-v-models="" className={cx("section-title-row")}>
                      <div
                        data-v-models=""
                        className={cx("section-marker")}
                      ></div>
                      <div data-v-models="">
                        <h2 data-v-models="">
                          {"Model & Training Provenance"}
                        </h2>
                        <p data-v-models="">
                          {
                            "Where this version came from and how it was trained."
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                  <div data-v-models="" className={cx("provenance-grid")}>
                    <div data-v-models="">
                      <span data-v-models="">{"Algorithm"}</span>
                      <strong data-v-models="">
                        {display(modelState.algorithm)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Camera angle"}</span>
                      <strong data-v-models="">
                        {display(cameraAngleLabel)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Prediction target"}</span>
                      <strong data-v-models="">
                        {display(predictionTargetLabel)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Feature schema"}</span>
                      <strong data-v-models="">
                        {display(modelState.feature_schema_version || "—")}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Training status"}</span>
                      <strong data-v-models="">
                        {display(modelState.training.status)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Dataset"}</span>
                      <strong data-v-models="">
                        {display(selectedDatasetText)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Total samples"}</span>
                      <strong data-v-models="">
                        {display(modelState.training.sample_count)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Train / test samples"}</span>
                      <strong data-v-models="">
                        {display(modelState.training.train_count)}
                        {" / "}
                        {display(modelState.training.test_count)}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Split strategy"}</span>
                      <strong data-v-models="">
                        {display(modelState.training.split_strategy || "—")}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Training started"}</span>
                      <strong data-v-models="">
                        {display(formatDate(modelState.training.started_at))}
                      </strong>
                    </div>
                    <div data-v-models="">
                      <span data-v-models="">{"Training completed"}</span>
                      <strong data-v-models="">
                        {display(formatDate(modelState.training.completed_at))}
                      </strong>
                    </div>
                  </div>
                </section>
                <section data-v-models="" className={cx("content-card")}>
                  <div data-v-models="" className={cx("section-header")}>
                    <div data-v-models="" className={cx("section-title-row")}>
                      <div
                        data-v-models=""
                        className={cx("section-marker")}
                      ></div>
                      <div data-v-models="">
                        <h2 data-v-models="">{"Feature Set"}</h2>
                        <p data-v-models="">
                          {
                            " Fixed inputs recorded for this FPPA M1 training run. "
                          }
                        </p>
                      </div>
                    </div>
                    <span data-v-models="" className={cx("section-badge")}>
                      {display(modelState.features.selected.length)}
                      {" FEATURES "}
                    </span>
                  </div>
                  <ModelFeatureState
                    data-v-models=""
                    features={modelState.features}
                  ></ModelFeatureState>
                </section>
                <section
                  data-v-models=""
                  className={cx("content-card evaluation-card")}
                >
                  <div data-v-models="" className={cx("section-header")}>
                    <div data-v-models="" className={cx("section-title-row")}>
                      <div
                        data-v-models=""
                        className={cx("section-marker")}
                      ></div>
                      <div data-v-models="">
                        <h2 data-v-models="">{"Evaluation Results"}</h2>
                        <p data-v-models="">
                          {
                            " FPPA good-versus-bad performance on the held-out test samples. "
                          }
                        </p>
                      </div>
                    </div>
                    <span
                      data-v-models=""
                      className={cx("section-badge", {
                        ready: evaluationAvailable,
                      })}
                    >
                      {display(
                        evaluationAvailable ? "EVALUATED" : "NO RESULTS",
                      )}
                    </span>
                  </div>
                  {evaluationAvailable ? (
                    <>
                      <div
                        data-v-models=""
                        className={cx("evaluation-context")}
                      >
                        <div data-v-models="">
                          <span data-v-models="">{"Training job"}</span>
                          <strong data-v-models="">
                            {"#"}
                            {display(modelState.training.job_id)}
                          </strong>
                        </div>
                        <div data-v-models="">
                          <span data-v-models="">{"Test samples"}</span>
                          <strong data-v-models="">
                            {display(modelState.training.test_count)}
                          </strong>
                        </div>
                        <div data-v-models="">
                          <span data-v-models="">{"Prediction target"}</span>
                          <strong data-v-models="">
                            {display(predictionTargetLabel)}
                          </strong>
                        </div>
                        <div data-v-models="">
                          <span data-v-models="">{"Camera angle"}</span>
                          <strong data-v-models="">
                            {display(cameraAngleLabel)}
                          </strong>
                        </div>
                      </div>
                      <ModelEvaluationState
                        data-v-models=""
                        evaluation={modelState.evaluation}
                      ></ModelEvaluationState>
                      <p data-v-models="" className={cx("evaluation-note")}>
                        {
                          " These are offline evaluation results from the held-out test set. They are not live predictions from the smartphone camera. Selecting another registered version displays that version's saved evaluation. "
                        }
                      </p>
                    </>
                  ) : (
                    <div data-v-models="" className={cx("empty-detail")}>
                      <strong data-v-models="">
                        {"No evaluation results available"}
                      </strong>
                      <p data-v-models="">
                        {
                          " This model does not have completed evaluation metrics and a non-empty test set recorded in its saved state. "
                        }
                      </p>
                    </div>
                  )}
                </section>
                {modelState.feature_warnings.length > 0 ? (
                  <section
                    data-v-models=""
                    className={cx("content-card warning-card")}
                  >
                    <div data-v-models="" className={cx("section-header")}>
                      <div data-v-models="" className={cx("section-title-row")}>
                        <div
                          data-v-models=""
                          className={cx("section-marker")}
                        ></div>
                        <div data-v-models="">
                          <h2 data-v-models="">
                            {"Validation & Feature Warnings"}
                          </h2>
                          <p data-v-models="">
                            {
                              "Scientific caveats recorded while producing this model."
                            }
                          </p>
                        </div>
                      </div>
                      <span
                        data-v-models=""
                        className={cx("section-badge warning-badge")}
                      >
                        {display(modelState.feature_warnings.length)}
                        {" WARNINGS "}
                      </span>
                    </div>
                    <div data-v-models="" className={cx("warning-list")}>
                      {each(modelState.feature_warnings).map(
                        ([index, warning]) => (
                          <div
                            data-v-models=""
                            key={`${index}-${warning}`}
                            className={cx("warning-item")}
                          >
                            {display(warning)}
                          </div>
                        ),
                      )}
                    </div>
                  </section>
                ) : null}
              </>
            ) : selectedModelId !== null ? (
              <section
                data-v-models=""
                role="status"
                className={cx("content-card empty-detail")}
              >
                <strong data-v-models="">
                  {"Unable to display the selected model"}
                </strong>
                <p data-v-models="">
                  {
                    " The registry is available, but the details for this model could not be loaded. Check the error message above and try selecting the version again. "
                  }
                </p>
                <button
                  data-v-models=""
                  type="button"
                  onClick={() => {
                    selectModel(selectedModelId);
                  }}
                  className={cx("secondary-button")}
                >
                  {" Retry loading model "}
                </button>
              </section>
            ) : null}
            <section
              data-v-models=""
              className={cx("content-card registry-card")}
            >
              <div data-v-models="" className={cx("section-header")}>
                <div data-v-models="" className={cx("section-title-row")}>
                  <div data-v-models="" className={cx("section-marker")}></div>
                  <div data-v-models="">
                    <h2 data-v-models="">{"Model Registry"}</h2>
                    <p data-v-models="">
                      {
                        " Select a registered version to inspect its provenance, features, and evaluation results. "
                      }
                    </p>
                  </div>
                </div>
                <span data-v-models="" className={cx("section-badge")}>
                  {display(models.length)}{" "}
                  {display(models.length === 1 ? "VERSION" : "VERSIONS")}
                </span>
              </div>
              <ModelRegistryTable
                data-v-models=""
                models={models}
                selectedModelId={selectedModelId}
                onSelect={selectModel}
              ></ModelRegistryTable>
            </section>
          </>
        )}
      </div>
    </>
  );
}
