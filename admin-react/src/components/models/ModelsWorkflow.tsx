import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './ModelsWorkflow.module.css';
export interface WorkflowStep {
    step: string;
    title: string;
    description: string;
}
export default function ModelsWorkflow(input: {
    steps: WorkflowStep[];
}) {
    const props = { ...{}, ...input };
    const { steps } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-models-workflow="" className={cx("workflow-grid")}>{each(steps).map(([_index, step]) => (<div data-v-models-workflow="" key={step.step} className={cx("workflow-card")}><div data-v-models-workflow="" className={cx("step-badge-row")}><span data-v-models-workflow="" className={cx("step-badge")}>{display(step.step)}</span>
        <span data-v-models-workflow="" className={cx("step-connector")}></span></div>
        <h3 data-v-models-workflow="" className={cx("step-title")}>{display(step.title)}</h3>
        <p data-v-models-workflow="" className={cx("step-description")}>{display(step.description)}</p></div>))}</div></>);
}
