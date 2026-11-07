import { bindStyles, display, scopeAttributes } from '../../presentation';
import styles from './SummaryCard.module.css';
export default function SummaryCard(input: {
    label: string;
    value: string | number;
    description: string;
    icon: string;
    variant?: 'samples' | 'correct' | 'incorrect' | 'version';
    statusIcon?: boolean;
}) {
    const props = { ...{}, ...input };
    const { label, value, description } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-summary-card="" className={cx("summary-card")}><span data-v-summary-card="" className={cx("summary-label")}>{display(label)}</span>
    <strong data-v-summary-card="" className={cx("summary-value")}>{display(value)}</strong>
    <span data-v-summary-card="" className={cx("summary-description")}>{display(description)}</span></div></>);
}
