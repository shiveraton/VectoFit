import type { Dataset } from "../../../services/datasetService";
import type { FeatureOption } from "../../../services/trainingService";
import AlgorithmSelector from "./AlgorithmSelector";
import DatasetSelector from "./DatasetSelector";
import FeatureSelector from "./FeatureSelector";
import HyperparameterPanel from "./HyperparameterPanel";
import ViewAngleSelector from "./ViewAngleSelector";
import { bindStyles, display, scopeAttributes } from '../../../presentation';
import styles from './TrainingConfiguration.module.css';
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
type Callbacks = {
    onToggleDataset?: (id: DatasetId) => void;
    onSetHyperparameter?: (key: string, value: number) => void;
    onSetTestSize?: (value: number) => void;
    onSetRandomSeed?: (value: number) => void;
    onStartTraining?: () => void;
};
export default function TrainingConfiguration(input: Props & Callbacks) {
    const props = { ...{}, ...input };
    const { availableDatasets, filteredDatasets, selectedDatasetIds, selectedDatasets, selectedViewAngle, features, hyperparameters, testSize, randomSeed, summaryText, canStartTraining, isTraining } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "toggle-dataset", id: DatasetId): void;
        (event: "set-hyperparameter", key: string, value: number): void;
        (event: "set-test-size", value: number): void;
        (event: "set-random-seed", value: number): void;
        (event: "start-training"): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "toggle-dataset":
            props.onToggleDataset?.(...args as [
                id: DatasetId
            ]);
            break;
        case "set-hyperparameter":
            props.onSetHyperparameter?.(...args as [
                key: string,
                value: number
            ]);
            break;
        case "set-test-size":
            props.onSetTestSize?.(...args as [
                value: number
            ]);
            break;
        case "set-random-seed":
            props.onSetRandomSeed?.(...args as [
                value: number
            ]);
            break;
        case "start-training":
            props.onStartTraining?.(...args as [
            ]);
            break;
    } }) as Emit;
    return (<><div {...scopeAttributes(input)} data-v-training-configuration="" className={cx("configuration-grid")}><ViewAngleSelector data-v-training-configuration=""></ViewAngleSelector>
    <DatasetSelector data-v-training-configuration="" availableDatasets={availableDatasets} filteredDatasets={filteredDatasets} selectedDatasetIds={selectedDatasetIds} selectedDatasets={selectedDatasets} selectedViewAngle={selectedViewAngle} onToggleDataset={(event) => { emit('toggle-dataset', event); }}></DatasetSelector>
    <FeatureSelector data-v-training-configuration="" features={features}></FeatureSelector>
    <AlgorithmSelector data-v-training-configuration=""></AlgorithmSelector>
    <HyperparameterPanel data-v-training-configuration="" hyperparameters={hyperparameters} testSize={testSize} randomSeed={randomSeed} onSetHyperparameter={(event) => { emit('set-hyperparameter', event.key, event.value); }} onSetTestSize={(event) => { emit('set-test-size', event); }} onSetRandomSeed={(event) => { emit('set-random-seed', event); }}></HyperparameterPanel></div>
    <footer {...scopeAttributes(input)} data-v-training-configuration="" className={cx("configuration-footer")}><div data-v-training-configuration="" className={cx("summary-copy")}><span data-v-training-configuration="" className={cx("footer-label")}>{"Configuration Summary"}</span>
    <strong data-v-training-configuration="">{display(summaryText)}</strong></div>
    <button data-v-training-configuration="" type="button" disabled={!canStartTraining || isTraining} onClick={() => { emit('start-training'); }} className={cx("primary-button")}>{(isTraining) ? (<span data-v-training-configuration="" aria-hidden="true" className={cx("button-spinner")}></span>) : (null)}
    {" "}
    {display(isTraining ? "Training..." : "Start Training")}</button></footer></>);
}
