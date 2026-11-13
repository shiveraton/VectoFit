import { Fragment } from 'react';
import type { WorkflowStep } from "../../services/trainingService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './TrainingWorkflow.module.css';
export default function TrainingWorkflow(input: {
    steps: WorkflowStep[];
}) {
    const props = { ...{}, ...input };
    const { steps } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-training-workflow="" className={cx("workflow")}>{each(steps).map(([index, step]) => (<Fragment key={step.number}><div data-v-training-workflow="" className={cx(['workflow-step', { active: step.active }])}><div data-v-training-workflow="" className={cx("workflow-number")}>{display(step.number)}</div>
        <strong data-v-training-workflow="">{display(step.title)}</strong>
        <span data-v-training-workflow="">{display(step.subtitle)}</span></div>
        {(index < steps.length - 1) ? (<div data-v-training-workflow="" className={cx("workflow-line")}></div>) : (null)}</Fragment>))}</div></>);
}
