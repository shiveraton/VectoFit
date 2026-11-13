import type { DeploymentStatus } from "../../services/modelService";
import { bindStyles, display, scopeAttributes } from '../../presentation';
import styles from './StatusBadge.module.css';
export default function StatusBadge(input: {
    status: DeploymentStatus;
    environment?: string;
}) {
    const props = { ...{}, ...input };
    const { status, environment } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-status-badge="" className={cx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", {
            'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': status === 'active',
            'bg-amber-500/10 text-amber-400 border-amber-500/20': status === 'building',
            'bg-rose-500/10 text-rose-400 border-rose-500/20': status === 'failed',
            'bg-slate-500/10 text-slate-400 border-slate-500/20': status === 'inactive',
        })}><span data-v-status-badge="" className={cx("h-1.5 w-1.5 rounded-full", {
            'bg-emerald-400 animate-pulse': status === 'active',
            'bg-amber-400 animate-spin': status === 'building',
            'bg-rose-400': status === 'failed',
            'bg-slate-400': status === 'inactive',
        })}></span>
    <span data-v-status-badge="" className={cx("capitalize")}>{display(status)}</span>
        {(environment) ? (<span data-v-status-badge="" className={cx("text-slate-500 font-normal")}>{"("}
        {display(environment)}
        {")"}</span>) : (null)}</div></>);
}
