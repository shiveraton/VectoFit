import { bindStyles, scopeAttributes } from '../../presentation';
import styles from './EvaluationEmptyState.module.css';
type Callbacks = {
    onConfigure?: () => void;
};
export default function EvaluationEmptyState(input: {} & Callbacks) {
    const props = { ...{}, ...input };
    const cx = bindStyles(styles);
    type Emit = {
        (event: "configure"): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "configure":
            props.onConfigure?.(...args as [
            ]);
            break;
    } }) as Emit;
    return (<><div {...scopeAttributes(input)} data-v-evaluation-empty-state="" className={cx("empty-state-container")}><div data-v-evaluation-empty-state="" className={cx("icon-badge")}><svg data-v-evaluation-empty-state="" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={cx("empty-icon")}><path data-v-evaluation-empty-state="" d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg></div>
    <h3 data-v-evaluation-empty-state="" className={cx("empty-title")}>{"No Evaluation Runs Found"}</h3>
    <p data-v-evaluation-empty-state="" className={cx("empty-description")}>{" There are currently no model evaluations recorded for this workspace. Select a target model checkpoint and reference dataset above to trigger your first biomechanical evaluation run. "}</p>
    <button data-v-evaluation-empty-state="" onClick={() => { emit('configure'); }} className={cx("primary-button")}><span data-v-evaluation-empty-state="" className={cx("button-icon")}>{"+"}</span>
    {" Configure New Evaluation "}</button></div></>);
}
