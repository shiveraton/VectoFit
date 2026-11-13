import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './EvaluationWorkflow.module.css';
export interface WorkflowStep {
    stepNumber: number;
    title: string;
    description: string;
    status: "completed" | "active" | "pending";
}
export default function EvaluationWorkflow(input: {
    steps: WorkflowStep[];
}) {
    const props = { ...{}, ...input };
    const { steps } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-evaluation-workflow="" className={cx("workflow-container")}><div data-v-evaluation-workflow="" className={cx("workflow-steps")}>{each(steps).map(([index, step]) => (<div data-v-evaluation-workflow="" key={step.stepNumber} className={cx("workflow-step", `status-${step.status}`)}><div data-v-evaluation-workflow="" className={cx("step-header")}><div data-v-evaluation-workflow="" className={cx("step-badge")}>{(step.status === 'completed') ? (<span data-v-evaluation-workflow="" className={cx("step-check")}>{"✓"}</span>) : (<span data-v-evaluation-workflow="">{display(step.stepNumber)}</span>)}</div>
        <span data-v-evaluation-workflow="" className={cx("step-status-tag")}>{display(step.status)}</span></div>
        <div data-v-evaluation-workflow="" className={cx("step-body")}><h3 data-v-evaluation-workflow="" className={cx("step-title")}>{display(step.title)}</h3>
        <p data-v-evaluation-workflow="" className={cx("step-description")}>{display(step.description)}</p></div>
        {(index < steps.length - 1) ? (<div data-v-evaluation-workflow="" className={cx("step-connector")}></div>) : (null)}</div>))}</div></div></>);
}
