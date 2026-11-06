import HyperparameterCard from "./HyperparameterCard";
import { FIXED_TRAINING_SETTINGS, TRAINING_PARAMETER_DEFINITIONS, } from "./trainingParameters";
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './HyperparameterPanel.module.css';
type Callbacks = {
    onSetHyperparameter?: (payload: {
        key: string;
        value: number;
    }) => void;
    onSetTestSize?: (value: number) => void;
    onSetRandomSeed?: (value: number) => void;
};
export default function HyperparameterPanel(input: {
    hyperparameters: Record<string, unknown>;
    testSize: number;
    randomSeed: number;
} & Callbacks) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    type Emit = {
        (event: "set-hyperparameter", payload: {
            key: string;
            value: number;
        }): void;
        (event: "set-test-size", value: number): void;
        (event: "set-random-seed", value: number): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "set-hyperparameter":
            props.onSetHyperparameter?.(...args as [
                payload: {
                    key: string;
                    value: number;
                }
            ]);
            break;
        case "set-test-size":
            props.onSetTestSize?.(...args as [
                value: number
            ]);
            break;
        case "set-random-seed":
            props.onSetRandomSeed?.(...args as [
                value: number
            ]);
            break;
    } }) as Emit;
    const valueFor = (key: string, fallback: number) => {
        const raw = props.hyperparameters[key];
        return typeof raw === "number" ? raw : fallback;
    };
    const parameterValues = (() => Object.fromEntries(TRAINING_PARAMETER_DEFINITIONS.map((definition) => [
        definition.key,
        definition.target === "hyperparameter"
            ? valueFor(definition.key, definition.defaultValue)
            : definition.target === "testSize"
                ? props.testSize
                : props.randomSeed,
    ])))();
    const parameterGroups = [
        { title: "XGBoost Hyperparameters", definitions: TRAINING_PARAMETER_DEFINITIONS.filter((item) => item.target === "hyperparameter") },
        { title: "Experiment Settings", definitions: TRAINING_PARAMETER_DEFINITIONS.filter((item) => item.target !== "hyperparameter") },
    ];
    const baselineDescription = (() => "Use the displayed baseline values as the reproducible starting configuration. Change them when the experiment requires a deliberate comparison.")();
    const emitUpdate = (definitionKey: string, value: number) => {
        const definition = TRAINING_PARAMETER_DEFINITIONS.find((item) => item.key === definitionKey);
        if (!definition)
            return;
        if (definition.target === "hyperparameter") {
            emit("set-hyperparameter", { key: definition.key, value });
        }
        else if (definition.target === "testSize") {
            emit("set-test-size", value);
        }
        else {
            emit("set-random-seed", value);
        }
    };
    return (<><section {...scopeAttributes(input)} data-v-hyperparameter-panel="" className={cx("configuration-section wide-section")}><div data-v-hyperparameter-panel="" className={cx("configuration-label")}><div data-v-hyperparameter-panel=""><strong data-v-hyperparameter-panel="">{"Training Parameters"}</strong>
    <span data-v-hyperparameter-panel="">{"Configure the XGBoost baseline and reproducible experiment settings."}</span></div></div>
    <div data-v-hyperparameter-panel="" className={cx("parameter-intro")}><div data-v-hyperparameter-panel=""><strong data-v-hyperparameter-panel="">{"How to use these controls"}</strong>
    <p data-v-hyperparameter-panel="">{display(baselineDescription)}</p></div>
    <span data-v-hyperparameter-panel="" className={cx("parameter-count")}>{display(TRAINING_PARAMETER_DEFINITIONS.length)}
    {" settings "}</span></div>
        {each(parameterGroups).map(([_index, group]) => (<section data-v-hyperparameter-panel="" key={group.title}><h3 data-v-hyperparameter-panel="">{display(group.title)}</h3>
        <div data-v-hyperparameter-panel="" className={cx("parameter-grid")}>{each(group.definitions).map(([_index, definition]) => (<HyperparameterCard data-v-hyperparameter-panel="" key={definition.key} definition={definition} modelValue={Number(parameterValues[definition.key])} onUpdate={(event) => { emitUpdate(definition.key, event); }}></HyperparameterCard>))}</div></section>))}
    <div data-v-hyperparameter-panel="" className={cx("fixed-parameters")}>{each(FIXED_TRAINING_SETTINGS).map(([_index, setting]) => (<span data-v-hyperparameter-panel="" key={setting.label}><strong data-v-hyperparameter-panel="">{display(setting.label)}</strong>
        <code data-v-hyperparameter-panel="">{display(setting.value)}</code></span>))}</div></section></>);
}
