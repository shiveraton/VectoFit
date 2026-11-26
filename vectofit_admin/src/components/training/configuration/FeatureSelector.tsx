import type { FeatureOption } from "../../../services/trainingService";
import {
  bindStyles,
  each,
  display,
  scopeAttributes,
} from "../../../presentation";
import styles from "./FeatureSelector.module.css";
export default function FeatureSelector(input: {
  features: FeatureOption[];
  onToggle: (id: string) => void;
  disabled?: boolean;
}) {
  const props = { ...{}, ...input };
  const cx = bindStyles(styles);
  const featureDescriptions: Record<string, string> = {
    fppa_l_bottom: "Signed left knee angle at squat bottom.",
    fppa_r_bottom: "Signed right knee angle at squat bottom.",
    fppa_l_peak: "Signed left FPPA at its largest deviation in the repetition.",
    fppa_r_peak:
      "Signed right FPPA at its largest deviation in the repetition.",
    asym_bottom: "Absolute left-right FPPA difference at squat bottom.",
    asym_peak: "Absolute left-right difference between peak FPPA values.",
  };
  return (
    <>
      <section
        {...scopeAttributes(input)}
        data-v-feature-selector=""
        className={cx("configuration-section")}
      >
        <div data-v-feature-selector="" className={cx("configuration-label")}>
          <div data-v-feature-selector="">
            <strong data-v-feature-selector="">
              {"Input features"}
            </strong>
            <span data-v-feature-selector="">
              {"Choose FPPA v2 inputs for this run. All six are selected by default."}
            </span>
          </div>
        </div>
        <div data-v-feature-selector="" className={cx("feature-selection")}>
          {each(props.features).map(([_index, feature]) => (
            <label
              data-v-feature-selector=""
              key={feature.id}
              className={cx(["feature-option", { selected: feature.selected }])}
            >
              <input
                data-v-feature-selector=""
                type="checkbox"
                checked={feature.selected}
                disabled={props.disabled}
                onChange={() => props.onToggle(feature.id)}
                className={cx("check-box")}
              />
              <span data-v-feature-selector="" className={cx("feature-copy")}>
                <strong data-v-feature-selector="">
                  {display(feature.name)}
                </strong>
                <small data-v-feature-selector="">
                  {display(
                    featureDescriptions[feature.id] ||
                      "Selected model feature.",
                  )}
                </small>
              </span>
            </label>
          ))}
        </div>
        <p data-v-feature-selector="" role="status" className={cx("feature-note")}>
          {props.features.filter((feature) => feature.selected).length} of {props.features.length} selected.
          {props.features.every((feature) => !feature.selected)
            ? " Select at least one feature to start training."
            : " Selection is saved with the model; changing inputs requires a new training run."}
        </p>
      </section>
    </>
  );
}
