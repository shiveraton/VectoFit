import type { EvaluationModel, EvaluationMetric, } from "../../hooks/useEvaluation";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './EvaluationConfigGrid.module.css';
interface Props {
    selectedDataset: Record<string, unknown> | null;
    selectedModelId: string | null;
    models: EvaluationModel[];
    metrics: EvaluationMetric[];
    summaryText: string;
}
type Callbacks = {
    onSelectModel?: (modelId: string) => void;
    onToggleMetric?: (metricId: string) => void;
    onStartEvaluation?: () => void;
};
export default function EvaluationConfigGrid(input: Props & Callbacks) {
    const props = { ...{}, ...input };
    const { selectedDataset, selectedModelId, models, metrics, summaryText } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "select-model", modelId: string): void;
        (event: "toggle-metric", metricId: string): void;
        (event: "start-evaluation"): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "select-model":
            props.onSelectModel?.(...args as [
                modelId: string
            ]);
            break;
        case "toggle-metric":
            props.onToggleMetric?.(...args as [
                metricId: string
            ]);
            break;
        case "start-evaluation":
            props.onStartEvaluation?.(...args as [
            ]);
            break;
    } }) as Emit;
    return (<><div {...scopeAttributes(input)} data-v-evaluation-config-grid="" className={cx("config-grid-container")}><div data-v-evaluation-config-grid="" className={cx("config-sections")}><div data-v-evaluation-config-grid="" className={cx("config-card")}><div data-v-evaluation-config-grid="" className={cx("card-header")}><span data-v-evaluation-config-grid="" className={cx("card-step")}>{"01"}</span>
    <div data-v-evaluation-config-grid=""><h3 data-v-evaluation-config-grid="">{"Target Model Checkpoint"}</h3>
    <p data-v-evaluation-config-grid="">{"Select a trained model version to benchmark."}</p></div></div>
    <div data-v-evaluation-config-grid="" className={cx("model-list")}>{each(models).map(([_index, model]) => (<div data-v-evaluation-config-grid="" key={model.id} onClick={() => { emit('select-model', model.id); }} className={cx("model-option", { selected: model.id === selectedModelId })}><div data-v-evaluation-config-grid="" className={cx("model-radio")}>{(model.id === selectedModelId) ? (<span data-v-evaluation-config-grid="" className={cx("radio-inner")}></span>) : (null)}</div>
        <div data-v-evaluation-config-grid="" className={cx("model-details")}><div data-v-evaluation-config-grid="" className={cx("model-name-row")}><span data-v-evaluation-config-grid="" className={cx("model-name")}>{display(model.name)}</span>
        <span data-v-evaluation-config-grid="" className={cx("model-version")}>{"v"}
        {display(model.version)}</span></div>
        <div data-v-evaluation-config-grid="" className={cx("model-meta")}><span data-v-evaluation-config-grid="" className={cx("model-type")}>{display(model.type)}</span>
            {(model.accuracy) ? (<span data-v-evaluation-config-grid="" className={cx("model-accuracy")}>{" Prev. Acc: "}
            {display(model.accuracy)}
            {"% "}</span>) : (null)}</div></div></div>))}</div></div>
    <div data-v-evaluation-config-grid="" className={cx("config-card")}><div data-v-evaluation-config-grid="" className={cx("card-header")}><span data-v-evaluation-config-grid="" className={cx("card-step")}>{"02"}</span>
    <div data-v-evaluation-config-grid=""><h3 data-v-evaluation-config-grid="">{"Benchmark Metrics"}</h3>
    <p data-v-evaluation-config-grid="">{"Toggle biomechanical & vector metrics for scoring."}</p></div></div>
    <div data-v-evaluation-config-grid="" className={cx("metrics-list")}>{each(metrics).map(([_index, metric]) => (<div data-v-evaluation-config-grid="" key={metric.id} onClick={() => { emit('toggle-metric', metric.id); }} className={cx("metric-option", { active: metric.selected })}><div data-v-evaluation-config-grid="" className={cx("metric-checkbox")}>{(metric.selected) ? (<span data-v-evaluation-config-grid="" className={cx("check-icon")}>{"✓"}</span>) : (null)}</div>
        <div data-v-evaluation-config-grid="" className={cx("metric-info")}><div data-v-evaluation-config-grid="" className={cx("metric-header-row")}><span data-v-evaluation-config-grid="" className={cx("metric-name")}>{display(metric.name)}</span>
        <span data-v-evaluation-config-grid="" className={cx("category-tag")}>{display(metric.category)}</span></div>
        <p data-v-evaluation-config-grid="" className={cx("metric-description")}>{display(metric.description)}</p></div></div>))}</div></div></div>
    <div data-v-evaluation-config-grid="" className={cx("config-footer")}><div data-v-evaluation-config-grid="" className={cx("summary-info")}><span data-v-evaluation-config-grid="" className={cx("summary-label")}>{"CONFIG SUMMARY"}</span>
    <p data-v-evaluation-config-grid="" className={cx("summary-text")}>{display(summaryText)}</p></div>
    <button data-v-evaluation-config-grid="" disabled={!selectedModelId || !selectedDataset} onClick={() => { emit('start-evaluation'); }} className={cx("primary-button")}><span data-v-evaluation-config-grid="" className={cx("button-icon")}>{"▶"}</span>
    {" Run Evaluation "}</button></div></div></>);
}
