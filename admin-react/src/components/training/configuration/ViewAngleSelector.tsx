import { bindStyles, scopeAttributes } from '../../../presentation';
import styles from './ViewAngleSelector.module.css';
export default function ViewAngleSelector(input: {}) {
    const cx = bindStyles(styles);
    return (<><section {...scopeAttributes(input)} data-v-view-angle-selector="" className={cx("configuration-section wide-section")}><div data-v-view-angle-selector="" className={cx("configuration-label")}><div data-v-view-angle-selector=""><strong data-v-view-angle-selector="">{"View Angle"}</strong>
    <span data-v-view-angle-selector="">{"FPPA measures bilateral knee alignment from a front-facing camera view."}</span></div></div>
    <div data-v-view-angle-selector="" className={cx("view-options")}><div data-v-view-angle-selector="" aria-current="true" className={cx("view-option selected")}><span data-v-view-angle-selector="" aria-hidden="true" className={cx("view-icon")}>{"F"}</span>
    <span data-v-view-angle-selector="" className={cx("view-copy")}><strong data-v-view-angle-selector="">{"Frontal"}</strong>
    <small data-v-view-angle-selector="">{"Required FPPA view"}</small>
    <span data-v-view-angle-selector="">{"Training and assessment use the same frontal-plane measurement schema."}</span></span>
    <span data-v-view-angle-selector="" aria-hidden="true" className={cx("view-indicator")}></span></div></div></section></>);
}
