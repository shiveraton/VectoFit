import { bindStyles, scopeAttributes } from '../../../presentation';
import styles from './AlgorithmSelector.module.css';
export default function AlgorithmSelector(input: {}) {
    const cx = bindStyles(styles);
    return (<><section {...scopeAttributes(input)} data-v-algorithm-selector="" className={cx("configuration-section")}><div data-v-algorithm-selector="" className={cx("configuration-label")}><div data-v-algorithm-selector=""><strong data-v-algorithm-selector="">{"Current Model"}</strong>
    <span data-v-algorithm-selector="">{"The FPPA M1 experiment uses a fixed XGBoost classifier."}</span></div></div>
    <div data-v-algorithm-selector="" className={cx("algorithm-card selected")}><span data-v-algorithm-selector="" className={cx("algorithm-icon")}>{"XGB"}</span>
    <span data-v-algorithm-selector="" className={cx("algorithm-copy")}><strong data-v-algorithm-selector="">{"XGBoost · FPPA M1"}</strong>
    <span data-v-algorithm-selector="">{"Predicts human-reviewed good/bad knee-alignment labels from the fixed FPPA v2 feature schema."}</span></span></div>
    <p data-v-algorithm-selector="" className={cx("algorithm-note")}>{" M0 uses four FPPA features; M1 adds bilateral asymmetry. Both are XGBoost models. The fixed 10-degree threshold rule is evaluated separately on the M0 / M1 Results page. "}</p></section></>);
}
