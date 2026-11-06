import type { Dataset, ViewAngle } from "../../../services/datasetService";
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './DatasetSelector.module.css';
type DatasetId = number;
type Callbacks = {
    onToggleDataset?: (id: DatasetId) => void;
};
export default function DatasetSelector(input: {
    availableDatasets: Dataset[];
    filteredDatasets: Dataset[];
    selectedDatasetIds: DatasetId[];
    selectedDatasets: Dataset[];
    selectedViewAngle: ViewAngle | null;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { filteredDatasets, selectedDatasetIds, selectedViewAngle } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "toggle-dataset", id: DatasetId): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "toggle-dataset":
            props.onToggleDataset?.(...args as [
                id: DatasetId
            ]);
            break;
    } }) as Emit;
    const selectedCount = (() => props.selectedDatasets.length)();
    const statsFor = (dataset: Dataset) => props.selectedViewAngle
        ? dataset.angle_training_stats?.[props.selectedViewAngle]
        : undefined;
    const kneeExcludedLabels = [
        "borderline",
        "unassessable",
        "disputed",
        "missing",
    ] as const;
    const kneeCount = (dataset: Dataset, label: "good" | "bad" | (typeof kneeExcludedLabels)[number]) => Number(statsFor(dataset)?.knee_label_counts?.[label] ?? 0);
    const kneeExcludedCount = (dataset: Dataset) => kneeExcludedLabels.reduce((total, label) => total + kneeCount(dataset, label), 0);
    const selectedSamples = (() => props.selectedDatasets.reduce((total, dataset) => total + Number(statsFor(dataset)?.sample_count || 0), 0))();
    const selectedLabelledSamples = (() => props.selectedDatasets.reduce((total, dataset) => {
        const stats = statsFor(dataset);
        return total + Number(stats?.knee_target_sample_count || 0);
    }, 0))();
    const formatNumber = (value: number) => value.toLocaleString("en-US");
    return (<><section {...scopeAttributes(input)} data-v-dataset-selector="" className={cx("configuration-section wide-section")}><div data-v-dataset-selector="" className={cx("configuration-label")}><div data-v-dataset-selector=""><strong data-v-dataset-selector="">{"Datasets"}</strong>
    <span data-v-dataset-selector="">{"Select prepared datasets that belong to the same camera view."}</span></div></div>
    <div data-v-dataset-selector="" className={cx("dataset-selection")}>{each(filteredDatasets).map(([_index, dataset]) => (<button data-v-dataset-selector="" key={dataset.id} type="button" aria-pressed={selectedDatasetIds.includes(dataset.id)} onClick={() => { emit('toggle-dataset', dataset.id); }} className={cx([
                'dataset-option',
                { selected: selectedDatasetIds.includes(dataset.id) },
            ])}><span data-v-dataset-selector="" aria-hidden="true" className={cx("dataset-check")}>{display(selectedDatasetIds.includes(dataset.id) ? "✓" : "")}</span>
        <span data-v-dataset-selector="" className={cx("dataset-main")}><span data-v-dataset-selector="" className={cx("dataset-title-row")}><strong data-v-dataset-selector="">{display(dataset.name)}</strong>
        <small data-v-dataset-selector="">{"#"}
        {display(dataset.id)}</small></span>
        <span data-v-dataset-selector="" className={cx("dataset-meta")}>{(dataset.exercise_type) ? (<span data-v-dataset-selector="">{display(dataset.exercise_type)}</span>) : (null)}
        <span data-v-dataset-selector="">{display(kneeCount(dataset, "good"))}
        {" good knee · "}
        {display(kneeCount(dataset, "bad"))}
        {" bad knee"}</span>
            {(kneeExcludedCount(dataset) > 0) ? (<span data-v-dataset-selector="">{display(kneeExcludedCount(dataset))}
            {" non-trainable knee label"}
            {display(kneeExcludedCount(dataset) === 1 ? "" : "s")}
            {" excluded "}</span>) : (null)}
        <span data-v-dataset-selector="">{display(statsFor(dataset)?.knee_target_sample_count ?? 0)}
        {" usable knee labels "}</span>
        <span data-v-dataset-selector="">{display(statsFor(dataset)?.participant_count ?? 0)}
        {" participants"}</span>
        <span data-v-dataset-selector="">{display(statsFor(dataset)?.video_count ?? 0)}
        {" videos"}</span></span></span></button>))}
        {(!filteredDatasets.length) ? (<div data-v-dataset-selector="" className={cx("inline-empty")}><strong data-v-dataset-selector="">{display(selectedViewAngle
                ? "No training-ready datasets have labelled samples for this angle and target."
                : "Select a camera view to display compatible datasets.")}</strong></div>) : (null)}</div>
    <div data-v-dataset-selector="" className={cx("selection-summary")}><span data-v-dataset-selector=""><strong data-v-dataset-selector="">{display(selectedCount)}</strong>
    {" dataset"}
    {display(selectedCount === 1 ? "" : "s")}
    {" selected "}</span>
        {(selectedCount) ? (<span data-v-dataset-selector="">{display(formatNumber(selectedLabelledSamples))}
        {" labelled target samples · "}
        {display(formatNumber(selectedSamples))}
        {" available samples at selected angle "}</span>) : (<span data-v-dataset-selector="">{"Choose at least one dataset to train."}</span>)}</div>
    <p data-v-dataset-selector="" className={cx("selection-note")}>{" Counts reflect stored labels. Repetitions with invalid or incomplete landmarks are excluded during feature extraction, so the final training sample count may be lower. Only "}
    <strong data-v-dataset-selector="">{"good"}</strong>
    {" and "}
    <strong data-v-dataset-selector="">{"bad"}</strong>
    {" knee-alignment labels are trainable; borderline, unassessable, disputed, and missing labels are reported but excluded. "}</p></section></>);
}
