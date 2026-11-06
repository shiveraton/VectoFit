import { useState } from 'react';
import type { CSSProperties } from 'react';
import ParameterSimulation from "./ParameterSimulation";
import type { TrainingParameterDefinition } from "./trainingParameters";
import Transition from '../../../Transition';
import { bindStyles, display, scopeAttributes } from '../../../presentation';
import styles from './HyperparameterCard.module.css';
type Callbacks = {
    onUpdate?: (value: number) => void;
};
export default function HyperparameterCard(input: {
    definition: TrainingParameterDefinition;
    modelValue: number;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { definition, modelValue } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "update", value: number): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "update":
            props.onUpdate?.(...args as [
                value: number
            ]);
            break;
    } }) as Emit;
    const [showHelp, setShowHelp] = useState(false);
    const progress = (() => {
        const range = props.definition.max - props.definition.min;
        if (!range)
            return 0;
        return ((props.modelValue - props.definition.min) / range) * 100;
    })();
    const displayValue = (() => {
        const value = props.modelValue;
        if (props.definition.format === "percent") {
            return `${Math.round(value * 100)}%`;
        }
        if (props.definition.format === "decimal") {
            return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
        }
        return Math.round(value).toLocaleString("en-US");
    })();
    const updateValue = (rawValue: string | number) => {
        const numericValue = Number(rawValue);
        if (!Number.isFinite(numericValue))
            return;
        const clamped = Math.min(props.definition.max, Math.max(props.definition.min, numericValue));
        emit("update", clamped);
    };
    return (<><article {...scopeAttributes(input)} data-v-hyperparameter-card="" className={cx("parameter-card")}><header data-v-hyperparameter-card="" className={cx("parameter-header")}><div data-v-hyperparameter-card="" className={cx("parameter-heading")}><span data-v-hyperparameter-card="" className={cx("parameter-title")}>{display(definition.title)}</span>
    <span data-v-hyperparameter-card="" className={cx("technical-name")}>{display(definition.technicalName)}</span></div>
    <button data-v-hyperparameter-card="" type="button" aria-expanded={showHelp} aria-label={`Explain ${definition.title}`} onClick={() => { setShowHelp(!showHelp); }} className={cx("help-button")}>{" ? "}</button></header>
    <div data-v-hyperparameter-card="" className={cx("parameter-question")}>{display(definition.question)}</div>
    <div data-v-hyperparameter-card="" className={cx("parameter-control")}>{(definition.inputType === 'range') ? (<input data-v-hyperparameter-card="" type="range" min={definition.min} max={definition.max} step={definition.step} value={modelValue} style={{ '--parameter-progress': `${Math.min(100, Math.max(0, progress))}%` } as CSSProperties} aria-label={definition.title} onChange={(event) => { updateValue((event.target as HTMLInputElement).value); }} className={cx("parameter-range")}/>) : (<input data-v-hyperparameter-card="" type="number" min={definition.min} max={definition.max} step={definition.step} value={modelValue} aria-label={definition.title} onChange={(event) => { updateValue((event.target as HTMLInputElement).value); }} className={cx("parameter-number")}/>)}
    <output data-v-hyperparameter-card="" className={cx("parameter-value")}>{display(displayValue)}</output></div>
    <div data-v-hyperparameter-card="" className={cx("parameter-scale")}><span data-v-hyperparameter-card="">{display(definition.lowLabel)}</span>
    <span data-v-hyperparameter-card="">{display(definition.highLabel)}</span></div>
    <ParameterSimulation data-v-hyperparameter-card="" variant={definition.simulation} progress={progress}></ParameterSimulation>
    <div data-v-hyperparameter-card="" className={cx("parameter-recommendation")}><span data-v-hyperparameter-card="">{"Baseline"}</span>
    <strong data-v-hyperparameter-card="">{display(definition.recommended)}</strong></div>
    <Transition name="help-fade" classes={styles}>{(showHelp) ? (<div data-v-hyperparameter-card="" className={cx("parameter-help")}><p data-v-hyperparameter-card="">{display(definition.description)}</p>
        <div data-v-hyperparameter-card="" className={cx("help-effects")}><span data-v-hyperparameter-card=""><strong data-v-hyperparameter-card="">{"Lower:"}</strong>
        {" "}
        {display(definition.lowEffect)}</span>
        <span data-v-hyperparameter-card=""><strong data-v-hyperparameter-card="">{"Higher:"}</strong>
        {" "}
        {display(definition.highEffect)}</span></div></div>) : (null)}</Transition></article></>);
}
