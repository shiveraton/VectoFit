import { useRef } from "react";
import SummaryCard from "../../components/datasets/SummaryCard";
import TrainingConfiguration from "../../components/training/configuration/TrainingConfiguration";
import TrainingResult from "../../components/training/results/TrainingResult";
import { useTraining } from "../../hooks/useTraining";
import { bindStyles, each, display, scopeAttributes } from "../../presentation";
import styles from "./Training.module.css";
export default function Training(input: {}) {
  const cx = bindStyles(styles);
  const configurationSection = useRef<HTMLElement | null>(null);
  const {
    features,
    selectedDatasets,
    selectedDatasetIds,
    selectedViewAngle,
    hyperparameters,
    summaryCards,
    configSummaryText,
    canStartTraining,
    isLoading,
    isTraining,
    error,
    toggleDataset,
    setHyperparameter,
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
  const selectedJobId = selectedJob?.id ?? null;
  const setSelectedJobId = (id: number) => selectJob(id);
  const latestJob = (() => selectedJob)();
  const configurationStatus = (() => {
    if (isTraining) return "TRAINING";
    return canStartTraining ? "READY" : "INCOMPLETE";
  })();
  const scrollToConfiguration = () => {
    configurationSection.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };
  return (
    <>
      <div
        {...scopeAttributes(input)}
        data-v-training=""
        className={cx("training-page")}
      >
        <header data-v-training="" className={cx("page-header")}>
          <div data-v-training="" className={cx("page-heading")}>
            <div data-v-training="" className={cx("eyebrow")}>
              <span
                data-v-training=""
                aria-hidden="true"
                className={cx("eyebrow-dot")}
              ></span>
              {" VECTOFIT MODEL TRAINING "}
            </div>
            <h1 data-v-training="">{"Training"}</h1>
            <p data-v-training="">
              {
                " Train and inspect frontal-plane knee-alignment models using FPPA v2. "
              }
            </p>
          </div>
          <button
            data-v-training=""
            type="button"
            onClick={() => scrollToConfiguration()}
            className={cx("primary-button")}
          >
            <span
              data-v-training=""
              aria-hidden="true"
              className={cx("button-icon")}
            >
              {"+"}
            </span>
            {" New Training Run "}
          </button>
        </header>
        <section
          data-v-training=""
          aria-label="FPPA training history"
          className={cx("content-card history-card")}
        >
          <div data-v-training="" className={cx("section-header")}>
            <h2 data-v-training="">{"FPPA Training History"}</h2>
            {trainingJobs.length ? (
              <select
                data-v-training=""
                value={selectedJobId ?? ""}
                onChange={(event) =>
                  setSelectedJobId(Number(event.target.value))
                }
                aria-label="Select an FPPA training run"
                className={cx("job-select")}
              >
                {each(trainingJobs).map(([_index, job]) => (
                  <option data-v-training="" key={job.id} value={job.id}>
                    {display(job.id)}
                    {" – "}
                    {display(formatDate(job.created_at))}
                    {" – "}
                    {display(job.status)}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
          {!trainingJobs.length ? (
            <p data-v-training="" className={cx("history-empty")}>
              {
                " No FPPA v2 runs recorded yet. Start a run to create the first M1 model. "
              }
            </p>
          ) : null}
        </section>
        <section
          data-v-training=""
          aria-label="FPPA training summary"
          className={cx("summary-grid")}
        >
          {each(summaryCards).map(([_index, card]) => (
            <SummaryCard
              data-v-training=""
              key={card.label}
              {...card}
            ></SummaryCard>
          ))}
        </section>
        <section
          data-v-training=""
          ref={configurationSection}
          className={cx("content-card")}
        >
          <div data-v-training="" className={cx("section-header")}>
            <div data-v-training="" className={cx("section-title-row")}>
              <div
                data-v-training=""
                aria-hidden="true"
                className={cx("section-marker")}
              ></div>
              <div data-v-training="">
                <h2 data-v-training="">{"Training Configuration"}</h2>
                <p data-v-training="">
                  {
                    " Configure an FPPA v2 M1 training experiment for the frontal view. "
                  }
                </p>
              </div>
            </div>
            <span
              data-v-training=""
              className={cx([
                "status-badge",
                {
                  ready: configurationStatus === "READY",
                  running: configurationStatus === "TRAINING",
                },
              ])}
            >
              {display(configurationStatus)}
            </span>
          </div>
          {error ? (
            <div data-v-training="" role="alert" className={cx("error-banner")}>
              {display(error)}
            </div>
          ) : null}
          {isLoading ? (
            <div
              data-v-training=""
              aria-live="polite"
              className={cx("loading-state")}
            >
              <span
                data-v-training=""
                aria-hidden="true"
                className={cx("loading-dot")}
              ></span>
              {" Loading training configuration... "}
            </div>
          ) : (
            <TrainingConfiguration
              data-v-training=""
              availableDatasets={availableDatasets}
              filteredDatasets={filteredDatasets}
              selectedDatasetIds={selectedDatasetIds}
              selectedDatasets={selectedDatasets}
              selectedViewAngle={selectedViewAngle}
              features={features}
              hyperparameters={hyperparameters}
              summaryText={configSummaryText}
              canStartTraining={canStartTraining}
              isTraining={isTraining}
              onToggleDataset={toggleDataset}
              onSetHyperparameter={setHyperparameter}
              onStartTraining={handleStartTraining}
            ></TrainingConfiguration>
          )}
        </section>
        <section data-v-training="" className={cx("content-card")}>
          <div data-v-training="" className={cx("section-header")}>
            <div data-v-training="" className={cx("section-title-row")}>
              <div
                data-v-training=""
                aria-hidden="true"
                className={cx("section-marker")}
              ></div>
              <div data-v-training="">
                <h2 data-v-training="">{"Training Result"}</h2>
                <p data-v-training="">
                  {
                    " Held-out evaluation for the selected FPPA v2 training run. "
                  }
                </p>
              </div>
            </div>
            {latestJob ? (
              <span
                data-v-training=""
                className={cx([
                  "status-badge",
                  {
                    ready: latestJob.status === "COMPLETED",
                    running:
                      latestJob.status === "RUNNING" ||
                      latestJob.status === "PENDING",
                    failed: latestJob.status === "FAILED",
                  },
                ])}
              >
                {display(latestJob.status)}
              </span>
            ) : null}
          </div>
          <TrainingResult data-v-training="" job={latestJob}></TrainingResult>
        </section>
      </div>
    </>
  );
}
