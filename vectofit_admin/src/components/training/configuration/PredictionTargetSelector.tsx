import type { PredictionTarget } from "../../../services/trainingService";
import { bindStyles, scopeAttributes } from '../../../presentation';
import styles from './PredictionTargetSelector.module.css';
type Callbacks = {
    onUpdateModelValue?: (value: PredictionTarget) => void;
};
export default function PredictionTargetSelector(input: {
    modelValue: PredictionTarget;
} & Callbacks) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    type Emit = {
        (event: "update:modelValue", value: PredictionTarget): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "update:modelValue":
            props.onUpdateModelValue?.(...args as [
                value: PredictionTarget
            ]);
            break;
    } }) as Emit;
    return (<><section {...scopeAttributes(input)} data-v-prediction-target-selector="" className={cx("configuration-section wide-section")}><div data-v-prediction-target-selector="" className={cx("configuration-label")}><div data-v-prediction-target-selector=""><strong data-v-prediction-target-selector="">{"Learning Target"}</strong>
    <span data-v-prediction-target-selector="">{"Choose what the classifier should learn from each repetition."}</span></div></div>
    <div data-v-prediction-target-selector="" className={cx("target-options")}><button data-v-prediction-target-selector="" type="button" onClick={() => { emit('update:modelValue', 'binary_form'); }} className={cx("target-option", { selected: props.modelValue === 'binary_form' })}><strong data-v-prediction-target-selector="">{"Form quality"}</strong>
    <span data-v-prediction-target-selector="">{"GOOD vs BAD — uses labelled repetitions, including source labels and human corrections."}</span>
    <small data-v-prediction-target-selector="">{"Recommended baseline"}</small></button>
    <button data-v-prediction-target-selector="" type="button" onClick={() => { emit('update:modelValue', 'error_type'); }} className={cx("target-option", { selected: props.modelValue === 'error_type' })}><strong data-v-prediction-target-selector="">{"Error type"}</strong>
    <span data-v-prediction-target-selector="">{"Correct form vs specific error_label categories. Incorrect repetitions without an error label are excluded."}</span>
    <small data-v-prediction-target-selector="">{"Requires specific error labels"}</small></button>
    <button data-v-prediction-target-selector="" type="button" onClick={() => { emit('update:modelValue', 'knee_alignment'); }} className={cx("target-option", { selected: props.modelValue === 'knee_alignment' })}><strong data-v-prediction-target-selector="">{"Frontal-plane knee alignment"}</strong>
    <span data-v-prediction-target-selector="">{"Good vs bad final knee-annotation targets. Requires completed human knee annotations with agreement across annotators."}</span>
    <small data-v-prediction-target-selector="">{"Frontal / diagonal pilot target"}</small></button></div></section></>);
}
