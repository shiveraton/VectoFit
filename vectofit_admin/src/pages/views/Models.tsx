import { Link } from "react-router";
import { useModels } from "../../hooks/useModels";
import ModelCard from "../../components/models/ModelCard";
import ModelRegistryTable from "../../components/models/ModelRegistryTable";
import { bindStyles, each, display, scopeAttributes } from "../../presentation";
import styles from "./Models.module.css";
export default function Models(input: {}) {
  const cx = bindStyles(styles);
  const {
    models,
    modelState,
    selectedModelId,
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
            <h1 data-v-models="">{"Model Registry"}</h1>
            <p data-v-models="">
              {
                " Select a model version, review activation readiness, and manage frontal-plane knee-alignment inference. "
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
                    <Link data-v-models="" to={`/training?job=${modelState.training.job_id}#training-result`} className={cx("secondary-button")}>
                      View training results
                    </Link>
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
                {modelState.model_card ? (
                  <ModelCard
                    data-v-models=""
                    card={modelState.model_card}
                  ></ModelCard>
                ) : null}
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
                        " Select a version to review its readiness and activate it for inference. "
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
