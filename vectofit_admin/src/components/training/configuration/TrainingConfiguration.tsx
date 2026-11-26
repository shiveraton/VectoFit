import type { Dataset } from "../../../services/datasetService";
import type { FeatureOption } from "../../../services/trainingService";
import AlgorithmSelector from "./AlgorithmSelector";
import SplitSelector from "./SplitSelector";
import type { TrainingSplit } from "../../../services/trainingService";
import DatasetSelector from "./DatasetSelector";
import FeatureSelector from "./FeatureSelector";
import HyperparameterPanel from "./HyperparameterPanel";
import ViewAngleSelector from "./ViewAngleSelector";
import { bindStyles, display, scopeAttributes } from "../../../presentation";
import styles from "./TrainingConfiguration.module.css";
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
  summaryText: string;
  canStartTraining: boolean;
  isTraining: boolean;
  trainingSplit: TrainingSplit;
  onSplitChange: (value: TrainingSplit) => void;
  testSize: number;
  onTestSizeChange: (value: number) => void;
}
type Callbacks = {
  onToggleFeature: (id: string) => void;
  onToggleDataset?: (id: DatasetId) => void;
  onSetHyperparameter?: (key: string, value: number) => void;
  onStartTraining?: () => void;
};
export default function TrainingConfiguration(input: Props & Callbacks) {
  const props = { ...{}, ...input };
  const {
    availableDatasets,
    filteredDatasets,
    selectedDatasetIds,
    selectedDatasets,
    selectedViewAngle,
    features,
    hyperparameters,
    canStartTraining,
    isTraining,
  } = props;
  const cx = bindStyles(styles);
  type Emit = {
    (event: "toggle-dataset", id: DatasetId): void;
    (event: "set-hyperparameter", key: string, value: number): void;
    (event: "start-training"): void;
  };
  const emit: Emit = ((event: string, ...args: unknown[]) => {
    switch (event) {
      case "toggle-dataset":
        props.onToggleDataset?.(...(args as [id: DatasetId]));
        break;
      case "set-hyperparameter":
        props.onSetHyperparameter?.(...(args as [key: string, value: number]));
        break;
      case "start-training":
        props.onStartTraining?.(...(args as []));
        break;
    }
  }) as Emit;
  return (
    <>
      <div
        {...scopeAttributes(input)}
        data-v-training-configuration=""
        className={cx("configuration-grid")}
      >
        <ViewAngleSelector data-v-training-configuration=""></ViewAngleSelector>
        <DatasetSelector
          data-v-training-configuration=""
          availableDatasets={availableDatasets}
          filteredDatasets={filteredDatasets}
          selectedDatasetIds={selectedDatasetIds}
          selectedDatasets={selectedDatasets}
          selectedViewAngle={selectedViewAngle}
          onToggleDataset={(event) => {
            emit("toggle-dataset", event);
          }}
        ></DatasetSelector>
        <FeatureSelector
          data-v-training-configuration=""
          features={features}
          onToggle={props.onToggleFeature}
          disabled={isTraining}
        ></FeatureSelector>
        <div className={styles.modelSection}>
          <AlgorithmSelector data-v-training-configuration=""></AlgorithmSelector>
          <SplitSelector
            value={props.trainingSplit}
            onChange={props.onSplitChange}
            testSize={props.testSize}
            onTestSizeChange={props.onTestSizeChange}
            disabled={isTraining}
          />
        </div>
        <HyperparameterPanel
          data-v-training-configuration=""
          hyperparameters={hyperparameters}
          onSetHyperparameter={(event) => {
            emit("set-hyperparameter", event.key, event.value);
          }}
        ></HyperparameterPanel>
      </div>
      <footer
        {...scopeAttributes(input)}
        data-v-training-configuration=""
        className={cx("configuration-footer")}
      >
        <button
          data-v-training-configuration=""
          type="button"
          disabled={!canStartTraining || isTraining}
          onClick={() => {
            emit("start-training");
          }}
          className={cx("primary-button")}
        >
          {isTraining ? (
            <span
              data-v-training-configuration=""
              aria-hidden="true"
              className={cx("button-spinner")}
            ></span>
          ) : null}{" "}
          {display(isTraining ? "Training..." : "Start Training")}
        </button>
      </footer>
    </>
  );
}
