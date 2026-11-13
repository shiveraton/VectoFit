import { Fragment } from 'react';
import type { CSSProperties } from 'react';
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './ConfusionMatrix.module.css';
export default function ConfusionMatrix(input: {
    matrix: unknown;
    labels?: string[] | null;
}) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    const entries = (() => {
        const matrix = props.matrix;
        if (!Array.isArray(matrix) || matrix.length === 0) {
            return null;
        }
        const size = matrix.length;
        const parsed: number[][] = [];
        for (const row of matrix) {
            if (!Array.isArray(row) || row.length !== size) {
                return null;
            }
            const values = row.map((value) => Number(value));
            if (values.some((value) => !Number.isFinite(value))) {
                return null;
            }
            parsed.push(values);
        }
        return parsed;
    })();
    const matrixSize = (() => entries?.length ?? 0)();
    const classLabels = (() => {
        const size = matrixSize;
        const provided = (props.labels ?? []).filter((label): label is string => typeof label === "string" && label.trim() !== "");
        if (provided.length === size) {
            return provided;
        }
        if (size === 2) {
            return ["Bad", "Good"];
        }
        return Array.from({ length: size }, (_, index) => `Class ${index}`);
    })();
    const humanize = (label: string) => label
        .replace(/_/g, " ")
        .trim()
        .split(/\s+/)
        .map((word) => word.length
        ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        : word)
        .join(" ");
    const rowTotal = (row: number[]) => row.reduce((total, value) => total + value, 0);
    const cellPercent = (rowIndex: number, columnIndex: number) => {
        const row = entries?.[rowIndex];
        if (!row)
            return 0;
        const total = rowTotal(row);
        return total > 0 ? Math.round((row[columnIndex] / total) * 100) : 0;
    };
    const summary = (() => {
        return "Rows are the human-reviewed FPPA labels (bad or good); columns are the model predictions. Inspect which knee-alignment class is confused before activating the model.";
    })();
    return (<><section {...scopeAttributes(input)} data-v-confusion-matrix="" className={cx("result-panel")}><header data-v-confusion-matrix="" className={cx("result-panel-header")}><div data-v-confusion-matrix=""><h3 data-v-confusion-matrix="">{"Classification Results"}</h3>
    <p data-v-confusion-matrix="">{" How predictions compared with the known test-set labels. Rows are actual labels; columns are predicted labels. "}</p></div></header>
        {(entries) ? (<div data-v-confusion-matrix="" className={cx("matrix-legend")}>{each(classLabels).map(([index, label]) => (<span data-v-confusion-matrix="" key={`legend-${index}`}><strong data-v-confusion-matrix="">{display(index)}</strong>
            {" = "}
            {display(humanize(label))}</span>))}</div>) : (null)}
        {(entries) ? (<div data-v-confusion-matrix="" className={cx("matrix-scroll")}><div data-v-confusion-matrix="" style={{ '--matrix-size': matrixSize } as CSSProperties} className={cx("matrix-layout")}><div data-v-confusion-matrix="" className={cx("matrix-axis axis-corner")}>{"Actual ↓ / Predicted →"}</div>
        {each(classLabels).map(([index, label]) => (<div data-v-confusion-matrix="" key={`column-${index}`} title={humanize(label)} className={cx("matrix-axis column-label")}>{display(humanize(label))}</div>))}
            {each(entries).map(([rowIndex, row]) => (<Fragment key={`row-${rowIndex}`}><div data-v-confusion-matrix="" className={cx("matrix-axis row-label")}>{display(humanize(classLabels[rowIndex] ?? `Class ${rowIndex}`))}</div>
                {each(row).map(([columnIndex, count]) => (<div data-v-confusion-matrix="" key={`cell-${rowIndex}-${columnIndex}`} className={cx([
                        'matrix-cell',
                        rowIndex === columnIndex ? 'correct' : 'misclassified',
                    ])}><strong data-v-confusion-matrix="">{display(count)}</strong>
                <span data-v-confusion-matrix="">{display(cellPercent(rowIndex, columnIndex))}
                {"% of actual "}
                {display(humanize(classLabels[rowIndex] ?? `Class ${rowIndex}`).toLowerCase())}</span></div>))}</Fragment>))}</div></div>) : (<div data-v-confusion-matrix="" className={cx("panel-empty")}>{" No confusion matrix is available for this run. "}</div>)}
        {(entries) ? (<div data-v-confusion-matrix="" className={cx("matrix-summary")}><strong data-v-confusion-matrix="">{"What to watch:"}</strong>
        {" "}
        {display(summary)}</div>) : (null)}</section></>);
}
