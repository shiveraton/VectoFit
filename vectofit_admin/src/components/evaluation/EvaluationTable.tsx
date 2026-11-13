import type { CSSProperties } from 'react';
import type { EvaluationRecord } from "../../hooks/useEvaluation";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './EvaluationTable.module.css';
type Callbacks = {
    onInspect?: (evaluation: EvaluationRecord) => void;
    onDelete?: (id: string) => void;
};
export default function EvaluationTable(input: {
    evaluations: EvaluationRecord[];
} & Callbacks) {
    const props = { ...{}, ...input };
    const { evaluations } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "inspect", evaluation: EvaluationRecord): void;
        (event: "delete", id: string): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "inspect":
            props.onInspect?.(...args as [
                evaluation: EvaluationRecord
            ]);
            break;
        case "delete":
            props.onDelete?.(...args as [
                id: string
            ]);
            break;
    } }) as Emit;
    const getStatusClass = (status: EvaluationRecord["status"]) => {
        switch (status) {
            case "COMPLETED":
                return "badge-completed";
            case "RUNNING":
                return "badge-running";
            case "FAILED":
                return "badge-failed";
            case "PENDING":
                return "badge-pending";
            default:
                return "";
        }
    };
    const getScoreColor = (score: number) => {
        if (score >= 90)
            return "score-high";
        if (score >= 75)
            return "score-mid";
        return "score-low";
    };
    return (<><div {...scopeAttributes(input)} data-v-evaluation-table="" className={cx("table-container")}><table data-v-evaluation-table="" className={cx("evaluation-table")}><thead data-v-evaluation-table=""><tr data-v-evaluation-table=""><th data-v-evaluation-table="">{"EVAL ID"}</th>
    <th data-v-evaluation-table="">{"MODEL"}</th>
    <th data-v-evaluation-table="">{"DATASET"}</th>
    <th data-v-evaluation-table="">{"VECTOR SCORE"}</th>
    <th data-v-evaluation-table="">{"STATUS"}</th>
    <th data-v-evaluation-table="">{"CREATED"}</th>
    <th data-v-evaluation-table="">{"DURATION"}</th>
    <th data-v-evaluation-table="" className={cx("text-right")}>{"ACTIONS"}</th></tr></thead>
    <tbody data-v-evaluation-table="">{each(evaluations).map(([_index, item]) => (<tr data-v-evaluation-table="" key={item.id} className={cx("table-row")}><td data-v-evaluation-table="" className={cx("font-mono eval-id")}>{display(item.id)}</td>
        <td data-v-evaluation-table="" className={cx("font-medium text-main")}>{display(item.modelName)}</td>
        <td data-v-evaluation-table="" className={cx("text-muted")}>{display(item.datasetName)}</td>
        <td data-v-evaluation-table="">{(item.status === 'COMPLETED') ? (<div data-v-evaluation-table="" className={cx("score-wrapper")}><span data-v-evaluation-table="" className={cx("score-value", getScoreColor(item.score))}>{display(item.score.toFixed(1))}
            {"% "}</span>
            <div data-v-evaluation-table="" className={cx("score-bar-bg")}><div data-v-evaluation-table="" style={{ width: `${item.score}%` } as CSSProperties} className={cx("score-bar-fill", getScoreColor(item.score))}></div></div></div>) : (<span data-v-evaluation-table="" className={cx("text-muted")}>{"--"}</span>)}</td>
        <td data-v-evaluation-table=""><span data-v-evaluation-table="" className={cx("status-badge", getStatusClass(item.status))}><span data-v-evaluation-table="" className={cx("badge-dot")}></span>
        {" "}
        {display(item.status)}</span></td>
        <td data-v-evaluation-table="" className={cx("text-muted text-xs")}>{display(item.createdAt)}</td>
        <td data-v-evaluation-table="" className={cx("text-muted text-xs")}>{display(item.duration)}</td>
        <td data-v-evaluation-table="" className={cx("text-right")}><div data-v-evaluation-table="" className={cx("actions-group")}><button data-v-evaluation-table="" onClick={() => { emit('inspect', item); }} title="Inspect Evaluation" className={cx("action-button secondary")}>{" Inspect "}</button>
        <button data-v-evaluation-table="" onClick={() => { emit('delete', item.id); }} title="Delete Record" className={cx("action-button danger")}>{" ✕ "}</button></div></td></tr>))}</tbody></table></div></>);
}
