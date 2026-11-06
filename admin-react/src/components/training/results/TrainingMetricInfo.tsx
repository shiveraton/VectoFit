import { useState } from 'react';
import Transition from '../../../Transition';
import { bindStyles, display, scopeAttributes } from '../../../presentation';
import styles from './TrainingMetricInfo.module.css';
export default function TrainingMetricInfo(input: {
    title: string;
    value: string;
    question: string;
    description: string;
    interpretation: string;
    variant?: "default" | "primary";
}) {
    const props = { ...{ variant: "default" }, ...input };
    const { title, value, question, description, interpretation, variant } = props;
    const cx = bindStyles(styles);
    const [showInfo, setShowInfo] = useState(false);
    return (<><article {...scopeAttributes(input)} data-v-training-metric-info="" className={cx(['metric-card', { primary: variant === 'primary' }])}><header data-v-training-metric-info="" className={cx("metric-header")}><span data-v-training-metric-info="">{display(title)}</span>
    <button data-v-training-metric-info="" type="button" aria-expanded={showInfo} aria-label={`Explain ${title}`} onClick={() => { setShowInfo(!showInfo); }} className={cx("info-button")}>{" ? "}</button></header>
    <strong data-v-training-metric-info="" className={cx("metric-value")}>{display(value)}</strong>
    <p data-v-training-metric-info="" className={cx("metric-question")}>{display(question)}</p>
    <Transition name="metric-fade" classes={styles}>{(showInfo) ? (<div data-v-training-metric-info="" className={cx("metric-help")}><p data-v-training-metric-info="">{display(description)}</p>
        <span data-v-training-metric-info="">{display(interpretation)}</span></div>) : (null)}</Transition></article></>);
}
