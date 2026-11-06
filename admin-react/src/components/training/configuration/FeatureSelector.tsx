import type { FeatureOption } from "../../../services/trainingService";
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './FeatureSelector.module.css';
export default function FeatureSelector(input: {
    features: FeatureOption[];
}) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    const featureDescriptions: Record<string, string> = {
        fppa_l_bottom: "Signed left knee angle at squat bottom.",
        fppa_r_bottom: "Signed right knee angle at squat bottom.",
        fppa_l_peak: "Largest absolute filtered left FPPA in the repetition.",
        fppa_r_peak: "Largest absolute filtered right FPPA in the repetition.",
        asym_bottom: "Absolute left-right FPPA difference at squat bottom.",
        asym_peak: "Absolute left-right difference between peak FPPA values.",
    };
    return (<><section {...scopeAttributes(input)} data-v-feature-selector="" className={cx("configuration-section")}><div data-v-feature-selector="" className={cx("configuration-label")}><div data-v-feature-selector=""><strong data-v-feature-selector="">{"FPPA v2 Feature Schema"}</strong>
    <span data-v-feature-selector="">{"Six fixed inputs used by the current M1 model."}</span></div></div>
    <div data-v-feature-selector="" className={cx("feature-selection")}>{each(props.features).map(([_index, feature]) => (<div data-v-feature-selector="" key={feature.id} className={cx(['feature-option', { selected: feature.selected }])}><span data-v-feature-selector="" aria-hidden="true" className={cx("check-box")}>{display(feature.selected ? "✓" : "")}</span>
        <span data-v-feature-selector="" className={cx("feature-copy")}><strong data-v-feature-selector="">{display(feature.name)}</strong>
        <small data-v-feature-selector="">{display(featureDescriptions[feature.id] || "Selected model feature.")}</small></span></div>))}</div>
    <p data-v-feature-selector="" className={cx("feature-note")}>{" The fixed schema keeps training inputs aligned with frontal-plane FPPA assessment and model provenance. "}</p></section></>);
}
