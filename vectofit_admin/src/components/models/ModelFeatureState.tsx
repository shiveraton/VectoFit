import type { CSSProperties } from 'react';
import type { ModelState } from "../../services/modelService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './ModelFeatureState.module.css';
export default function ModelFeatureState(input: {
    features: ModelState["features"];
}) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    const featureLabels: Record<string, string> = {
        fppa_l_bottom: "Left FPPA at squat bottom",
        fppa_r_bottom: "Right FPPA at squat bottom",
        fppa_l_peak: "Left peak FPPA",
        fppa_r_peak: "Right peak FPPA",
        asym_bottom: "Bottom bilateral asymmetry",
        asym_peak: "Peak bilateral asymmetry",
    };
    const groups = (() => {
        const selected = new Set(props.features.selected);
        const fppaFeatures = [
            "fppa_l_bottom",
            "fppa_r_bottom",
            "fppa_l_peak",
            "fppa_r_peak",
            "asym_bottom",
            "asym_peak",
        ];
        return [
            {
                title: "FPPA v2 · M1 Input Features",
                features: fppaFeatures.filter((key) => selected.has(key)),
            },
        ].filter((group) => group.features.length > 0);
    })();
    const importanceRows = (() => Object.entries(props.features.importances)
        .map(([name, value]) => ({
        name,
        label: featureLabels[name] ?? name,
        value: Number(value),
    }))
        .filter((row) => Number.isFinite(row.value))
        .sort((a, b) => b.value - a.value))();
    const maxImportance = (() => importanceRows.reduce((max, row) => Math.max(max, row.value), 0))();
    const labelFor = (name: string) => featureLabels[name] ?? name;
    return (<><div {...scopeAttributes(input)} data-v-model-feature-state="" className={cx("feature-layout")}><div data-v-model-feature-state="" className={cx("feature-set")}>{each(groups).map(([_index, group]) => (<div data-v-model-feature-state="" key={group.title} className={cx("feature-group")}><div data-v-model-feature-state="" className={cx("group-title")}>{display(group.title)}</div>
        <div data-v-model-feature-state="" className={cx("feature-list")}>{each(group.features).map(([_index, feature]) => (<span data-v-model-feature-state="" key={feature} className={cx("feature-chip")}>{display(labelFor(feature))}</span>))}</div></div>))}</div>
    <div data-v-model-feature-state="" className={cx("importance-panel")}><div data-v-model-feature-state="" className={cx("subheading")}>{"Feature importance"}</div>
    <p data-v-model-feature-state="" className={cx("helper")}>{" Relative contribution reported by the trained XGBoost M1 model. "}</p>
        {(importanceRows.length) ? (<div data-v-model-feature-state="" className={cx("importance-list")}>{each(importanceRows).map(([_index, row]) => (<div data-v-model-feature-state="" key={row.name} className={cx("importance-row")}><div data-v-model-feature-state="" className={cx("importance-meta")}><span data-v-model-feature-state="">{display(row.label)}</span>
            <span data-v-model-feature-state="">{display((row.value * 100).toFixed(1))}
            {"% "}</span></div>
            <div data-v-model-feature-state="" className={cx("importance-track")}><div data-v-model-feature-state="" style={{
                    width: `${maxImportance ? (row.value / maxImportance) * 100 : 0}%`,
                } as CSSProperties} className={cx("importance-fill")}></div></div></div>))}</div>) : (<div data-v-model-feature-state="" className={cx("empty-detail")}>{" Feature importance is not available for this model. "}</div>)}</div></div></>);
}
