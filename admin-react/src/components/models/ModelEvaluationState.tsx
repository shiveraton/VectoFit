import { Fragment } from 'react';
import type { CSSProperties } from 'react';
import type { ModelState } from "../../services/modelService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './ModelEvaluationState.module.css';
export default function ModelEvaluationState(input: {
    evaluation: ModelState["evaluation"];
}) {
    const props = { ...{}, ...input };
    const { evaluation } = props;
    const cx = bindStyles(styles);
    const metricLabels: Record<string, string> = {
        accuracy: "Accuracy",
        balanced_accuracy: "Balanced Accuracy",
        precision: "Precision",
        recall: "Recall",
        f1: "F1 Score",
    };
    const metricValue = (key: string) => {
        const value = props.evaluation[key as keyof ModelState["evaluation"]];
        return typeof value === "number" ? value : null;
    };
    const formatMetric = (value: number | null) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;
    const classLabels = (() => {
        const mapping = props.evaluation.class_mapping ?? {};
        const matrix = props.evaluation.confusion_matrix ?? [];
        const size = Array.isArray(matrix) ? matrix.length : 0;
        return Array.from({ length: size }, (_, index) => mapping[String(index)] ?? `Class ${index}`);
    })();
    const confusionMatrix = (() => {
        const matrix = props.evaluation.confusion_matrix;
        if (!Array.isArray(matrix) || matrix.length === 0)
            return null;
        if (!matrix.every((row) => Array.isArray(row) && row.length === matrix.length)) {
            return null;
        }
        return matrix;
    })();
    const distributionRows = (() => {
        const overall = props.evaluation.overall_class_distribution ?? {};
        const test = props.evaluation.test_class_distribution ?? {};
        const mapping = props.evaluation.class_mapping ?? {};
        const mappingKeys = Object.keys(mapping).sort((a, b) => Number(a) - Number(b));
        if (mappingKeys.length) {
            return mappingKeys.map((key) => {
                const label = mapping[key];
                return {
                    key,
                    label,
                    overall: overall[label] ?? overall[key] ?? "—",
                    test: test[label] ?? test[key] ?? "—",
                };
            });
        }
        const keys = Array.from(new Set([...Object.keys(overall), ...Object.keys(test)])).sort((a, b) => a.localeCompare(b));
        return keys.map((key) => ({
            key,
            label: key,
            overall: overall[key] ?? "—",
            test: test[key] ?? "—",
        }));
    })();
    return (<><div {...scopeAttributes(input)} data-v-model-evaluation-state="" className={cx("evaluation-body")}><div data-v-model-evaluation-state="" className={cx("metric-grid")}>{each(Object.keys(metricLabels)).map(([_index, key]) => (<div data-v-model-evaluation-state="" key={key} className={cx("metric-item")}><span data-v-model-evaluation-state="" className={cx("metric-label")}>{display(metricLabels[key])}</span>
        <strong data-v-model-evaluation-state="">{display(formatMetric(metricValue(key)))}</strong></div>))}</div>
    <div data-v-model-evaluation-state="" className={cx("evaluation-bottom")}><div data-v-model-evaluation-state="" className={cx("matrix-wrap")}><div data-v-model-evaluation-state="" className={cx("subheading")}>{"Confusion matrix"}</div>
    <p data-v-model-evaluation-state="" className={cx("helper")}>{"Held-out classification results."}</p>
        {(confusionMatrix) ? (<div data-v-model-evaluation-state="" style={{
                gridTemplateColumns: `92px repeat(${classLabels.length}, minmax(0, 1fr))`,
            } as CSSProperties} className={cx("matrix")}><div data-v-model-evaluation-state="" className={cx("matrix-corner")}>{"Actual ↓ / Pred. →"}</div>
        {each(classLabels).map(([index, label]) => (<div data-v-model-evaluation-state="" key={`predicted-${index}`} className={cx("matrix-axis")}>{display(label)}</div>))}
            {each(confusionMatrix).map(([rowIndex, row]) => (<Fragment key={`actual-${rowIndex}`}><div data-v-model-evaluation-state="" className={cx("matrix-axis row-axis")}>{display(classLabels[rowIndex] ?? `Class ${rowIndex}`)}</div>
            {each(row).map(([colIndex, value]) => (<div data-v-model-evaluation-state="" key={`cell-${rowIndex}-${colIndex}`} className={cx("matrix-cell")}>{display(value)}</div>))}</Fragment>))}</div>) : (<div data-v-model-evaluation-state="" className={cx("matrix-empty")}>{" No square confusion matrix is available for this model. "}</div>)}</div>
    <div data-v-model-evaluation-state="" className={cx("distribution-wrap")}><div data-v-model-evaluation-state="" className={cx("subheading")}>{"Class distribution"}</div>
    <p data-v-model-evaluation-state="" className={cx("helper")}>{"Label counts retained with the training run."}</p>
        {(distributionRows.length) ? (<div data-v-model-evaluation-state="" className={cx("distribution-grid")}>{each(distributionRows).map(([_index, entry]) => (<div data-v-model-evaluation-state="" key={entry.key} className={cx("distribution-card")}><span data-v-model-evaluation-state="">{display(entry.label)}</span>
            <div data-v-model-evaluation-state="" className={cx("distribution-values")}><small data-v-model-evaluation-state="">{"Overall"}</small>
            <strong data-v-model-evaluation-state="">{display(entry.overall)}</strong>
            <small data-v-model-evaluation-state="">{"Test"}</small>
            <strong data-v-model-evaluation-state="">{display(entry.test)}</strong></div></div>))}</div>) : (<p data-v-model-evaluation-state="" className={cx("helper")}>{"No class distribution was recorded."}</p>)}</div></div>
        {(evaluation.per_class?.length) ? (<div data-v-model-evaluation-state="" className={cx("per-class-wrap")}><div data-v-model-evaluation-state="" className={cx("subheading")}>{"Per-class performance"}</div>
        <p data-v-model-evaluation-state="" className={cx("helper")}>{" Precision, recall, and F1 derived from the held-out confusion matrix. Support is the number of actual test samples for each class. "}</p>
        <div data-v-model-evaluation-state="" className={cx("per-class-scroll")}><div data-v-model-evaluation-state="" className={cx("per-class-table")}><div data-v-model-evaluation-state="" className={cx("per-class-row per-class-header")}><span data-v-model-evaluation-state="">{"Class"}</span>
        <span data-v-model-evaluation-state="">{"Support"}</span>
        <span data-v-model-evaluation-state="">{"Predicted"}</span>
        <span data-v-model-evaluation-state="">{"Precision"}</span>
        <span data-v-model-evaluation-state="">{"Recall"}</span>
        <span data-v-model-evaluation-state="">{"F1"}</span></div>
            {each(evaluation.per_class).map(([_index, row]) => (<div data-v-model-evaluation-state="" key={row.index} className={cx("per-class-row")}><strong data-v-model-evaluation-state="">{display(row.label)}</strong>
            <span data-v-model-evaluation-state="">{display(row.support)}</span>
            <span data-v-model-evaluation-state="">{display(row.predicted_count)}</span>
            <span data-v-model-evaluation-state="">{display(formatMetric(row.precision))}</span>
            <span data-v-model-evaluation-state="">{display(formatMetric(row.recall))}</span>
            <span data-v-model-evaluation-state="">{display(formatMetric(row.f1))}</span></div>))}</div></div></div>) : (null)}</div></>);
}
