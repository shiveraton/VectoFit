import { bindStyles, display, scopeAttributes } from '../../presentation';
import styles from './DatasetEmptyState.module.css';
type Callbacks = {
    onAction?: () => void;
};
export default function DatasetEmptyState(input: {
    title?: string;
    description?: string;
    buttonLabel?: string;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { title, description, buttonLabel } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "action"): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "action":
            props.onAction?.(...args as [
            ]);
            break;
    } }) as Emit;
    return (<><div {...scopeAttributes(input)} data-v-dataset-empty-state="" className={cx("empty-state")}><h3 data-v-dataset-empty-state="">{display(title || 'No datasets available')}</h3>
    <p data-v-dataset-empty-state="">{display(description || 'Create or upload your first dataset to start defining biomechanical squat features and training models.')}</p>
    <button data-v-dataset-empty-state="" onClick={() => { emit('action'); }} className={cx("secondary-button")}><span data-v-dataset-empty-state="" className={cx("button-icon")}>{"+"}</span>
    {" "}
    {display(buttonLabel || 'Create Dataset')}</button></div></>);
}
