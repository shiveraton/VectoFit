import ConfusionMatrix from "./ConfusionMatrix";
import FeatureImportance from "./FeatureImportance";
import TrainingMetricInfo from "./TrainingMetricInfo";
import { bindStyles, display, scopeAttributes } from "../../../presentation";
import styles from "./TrainingResult.module.css";
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
  completed_at?: string | null;
  started_at?: string | null;
  error_message?: string | null;
  metrics?: TrainingMetrics | null;
  hyperparameters?: Record<string, unknown> | null;
  feature_selection?: string[] | null;
  split_strategy?: string | null;
  dataset_names?: string[] | null;
  view_angle?: string | null;
  prediction_target?: string | null;
}
export default function TrainingResult(input: {
  job: TrainingResultJob | null;
}) {
  const props = { ...{}, ...input };
  const { job } = props;
  const cx = bindStyles(styles);
  const formatMetric = (value: unknown) => {
    if (typeof value !== "number" || !Number.isFinite(value)) return "--";
    return `${(value * 100).toFixed(1)}%`;
  };
  const featureImportance = (() => {
    const raw = props.job?.metrics?.feature_importances;
    if (!raw || typeof raw !== "object") return [];
    return Object.entries(raw)
      .filter(
        ([, value]) => typeof value === "number" && Number.isFinite(value),
      )
      .map(([name, value]) => ({ name, value: Number(value) }))
      .sort((a, b) => b.value - a.value);
  })();
  const confusionMatrix = (() =>
    props.job?.metrics?.confusion_matrix ?? null)();
  const targetNames = (() => {
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
  })();
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
    recallQuestion:
      "How well does the model identify both knee-alignment labels?",
    recallDescription:
      "Macro recall is the unweighted mean recall for good and bad knee-alignment labels.",
    recallInterpretation:
      "Each knee-alignment class contributes equally, so poor recall on either label lowers this score.",
    f1Title: "Macro F1",
  };
  const resultInterpretation = (() => {
    const f1 = props.job?.metrics?.f1;
    const balancedAccuracy = props.job?.metrics?.balanced_accuracy;
    if (typeof f1 !== "number" || typeof balancedAccuracy !== "number") {
      return "Review the available metrics, test-set counts, and confusion matrix before considering activation.";
    }
    return `The held-out test repetitions produced a macro F1 of ${formatMetric(f1)} and balanced accuracy of ${formatMetric(balancedAccuracy)}.`;
  })();
  return (
    <>
      {!job ? (
        <div
          {...scopeAttributes(input)}
          data-v-training-result=""
          className={cx("result-empty")}
        >
          <div data-v-training-result="" className={cx("result-empty-icon")}>
            {"M1"}
          </div>
          <h3 data-v-training-result="">{"No FPPA training result yet"}</h3>
          <p data-v-training-result="">
            {
              " Configure an experiment above and start training to generate held-out metrics, feature importance, and classification results. "
            }
          </p>
        </div>
      ) : (
        <div
          {...scopeAttributes(input)}
          data-v-training-result=""
          className={cx("result-content")}
        >
          {job.status === "RUNNING" || job.status === "PENDING" ? (
            <div
              data-v-training-result=""
              className={cx("run-state running-state")}
            >
              <span
                data-v-training-result=""
                aria-hidden="true"
                className={cx("state-icon")}
              >
                {"…"}
              </span>
              <div data-v-training-result="">
                <strong data-v-training-result="">
                  {"Training is in progress"}
                </strong>
                <p data-v-training-result="">
                  {
                    " The configuration is active. Final evaluation metrics will appear here once the job completes. "
                  }
                </p>
              </div>
            </div>
          ) : job.status === "FAILED" ? (
            <div
              data-v-training-result=""
              className={cx("run-state failed-state")}
            >
              <span
                data-v-training-result=""
                aria-hidden="true"
                className={cx("state-icon")}
              >
                {"!"}
              </span>
              <div data-v-training-result="">
                <strong data-v-training-result="">{"Training failed"}</strong>
                <p data-v-training-result="">
                  {display(
                    job.error_message ||
                      "No error message was returned by the training service.",
                  )}
                </p>
              </div>
            </div>
          ) : job.status === "COMPLETED" ? (
            <>
              <p data-v-training-result="">
                {
                  " Evaluation: leave-one-participant-out (LOPO). Train / test participants per fold: "
                }
                {display(job.metrics?.train_participant_count ?? "--")}
                {" / "}
                {display(job.metrics?.test_participant_count ?? "--")}
                {". "}
              </p>
              <div data-v-training-result="" className={cx("metrics-grid")}>
                <TrainingMetricInfo
                  data-v-training-result=""
                  title="Accuracy"
                  value={formatMetric(job.metrics?.accuracy)}
                  question="How often did the model make the correct overall decision?"
                  description="Accuracy is the proportion of held-out test repetitions classified correctly."
                  interpretation="High accuracy is useful, but it can hide class imbalance, so inspect balanced accuracy and the confusion matrix too."
                ></TrainingMetricInfo>
                <TrainingMetricInfo
                  data-v-training-result=""
                  title="Balanced Accuracy"
                  value={formatMetric(job.metrics?.balanced_accuracy)}
                  question="Did the model perform reasonably across every class?"
                  description="Balanced accuracy averages recall across target classes so each class contributes equally."
                  interpretation={metricCopy.balancedAccuracyDescription}
                ></TrainingMetricInfo>
                <TrainingMetricInfo
                  data-v-training-result=""
                  title={metricCopy.precisionTitle}
                  value={formatMetric(job.metrics?.precision)}
                  question={metricCopy.precisionQuestion}
                  description={metricCopy.precisionDescription}
                  interpretation={metricCopy.precisionInterpretation}
                ></TrainingMetricInfo>
                <TrainingMetricInfo
                  data-v-training-result=""
                  title={metricCopy.recallTitle}
                  value={formatMetric(job.metrics?.recall)}
                  question={metricCopy.recallQuestion}
                  description={metricCopy.recallDescription}
                  interpretation={metricCopy.recallInterpretation}
                ></TrainingMetricInfo>
                <TrainingMetricInfo
                  data-v-training-result=""
                  title={metricCopy.f1Title}
                  variant="primary"
                  value={formatMetric(job.metrics?.f1)}
                  question="How well does the model balance precision and recall?"
                  description="F1 combines precision and recall into a single score using their harmonic mean."
                  interpretation="Use F1 as a useful comparison metric, but do not interpret it without the test-set composition and confusion matrix."
                ></TrainingMetricInfo>
              </div>
              <div
                data-v-training-result=""
                className={cx("result-interpretation")}
              >
                <div
                  data-v-training-result=""
                  className={cx("interpretation-icon")}
                >
                  {"?"}
                </div>
                <div data-v-training-result="">
                  <strong data-v-training-result="">
                    {"What does this result mean?"}
                  </strong>
                  <p data-v-training-result="">
                    {display(resultInterpretation)}
                  </p>
                </div>
              </div>
              <div data-v-training-result="" className={cx("result-grid")}>
                <FeatureImportance
                  data-v-training-result=""
                  values={featureImportance}
                />
                <ConfusionMatrix
                  data-v-training-result=""
                  matrix={confusionMatrix}
                  labels={targetNames}
                ></ConfusionMatrix>
              </div>
            </>
          ) : null}
        </div>
      )}
    </>
  );
}
