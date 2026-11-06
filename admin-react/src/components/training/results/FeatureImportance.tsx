import type { CSSProperties } from 'react';
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './FeatureImportance.module.css';
export default function FeatureImportance(input: {
    values: Array<{
        name: string;
        value: number;
    }>;
}) {
    const props = { ...{}, ...input };
    const { values } = props;
    const cx = bindStyles(styles);
    const maximum = () => Math.max(...props.values.map((item) => item.value), 0.000001);
    return (<><section {...scopeAttributes(input)} data-v-feature-importance="" className={cx("result-panel")}><header data-v-feature-importance="" className={cx("result-panel-header")}><div data-v-feature-importance=""><h3 data-v-feature-importance="">{"What influenced the model?"}</h3>
    <p data-v-feature-importance="">{"Relative feature importance reported by the trained XGBoost model."}</p></div>
        {(values.length) ? (<span data-v-feature-importance="" className={cx("top-feature")}>{" Top: "}
        <strong data-v-feature-importance="">{display(values[0].name)}</strong></span>) : (null)}</header>
        {(values.length) ? (<div data-v-feature-importance="" className={cx("importance-list")}>{each(values).map(([_index, feature]) => (<div data-v-feature-importance="" key={feature.name} className={cx("importance-row")}><div data-v-feature-importance="" className={cx("importance-label")}><span data-v-feature-importance="">{display(feature.name)}</span>
            <strong data-v-feature-importance="">{display((feature.value * 100).toFixed(1))}
            {"%"}</strong></div>
            <div data-v-feature-importance="" className={cx("importance-track")}><div data-v-feature-importance="" style={{ width: `${(feature.value / maximum()) * 100}%` } as CSSProperties} className={cx("importance-fill")}></div></div></div>))}</div>) : (<div data-v-feature-importance="" className={cx("panel-empty")}>{"No feature importance data is available for this run."}</div>)}
    <div data-v-feature-importance="" className={cx("interpretation-box")}><span data-v-feature-importance="">{"How to interpret this"}</span>
    <p data-v-feature-importance="">{" Larger values indicate a greater contribution to the trained model's decision process. They do not mean the feature independently causes correct or incorrect squat form. "}</p></div></section></>);
}
