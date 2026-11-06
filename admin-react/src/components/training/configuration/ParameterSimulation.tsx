import type { CSSProperties } from 'react';
import type { ParameterSimulation } from "./trainingParameters";
import { bindStyles, each, display, scopeAttributes } from '../../../presentation';
import styles from './ParameterSimulation.module.css';
export default function ParameterSimulation(input: {
    variant: ParameterSimulation;
    progress: number;
}) {
    const props = { ...{ progress: 50 }, ...input };
    const { variant } = props;
    const cx = bindStyles(styles);
    const clampedProgress = () => Math.min(100, Math.max(0, props.progress));
    return (<><div {...scopeAttributes(input)} data-v-parameter-simulation="" aria-hidden="true" className={cx("simulation")}>{(variant === 'trees') ? (<div data-v-parameter-simulation="" className={cx("tree-simulation")}>{each(8).map(([_index, index]) => (<span data-v-parameter-simulation="" key={index} className={cx(['tree', { visible: index <= Math.max(1, Math.round((clampedProgress() / 100) * 8)) }])}></span>))}</div>) : ((variant === 'depth') ? (<div data-v-parameter-simulation="" className={cx("depth-simulation")}>{each(4).map(([_index, index]) => (<span data-v-parameter-simulation="" key={index} className={cx(['level', { active: index <= Math.max(1, Math.ceil((clampedProgress() / 100) * 4)) }])}><i data-v-parameter-simulation=""></i>
            <i data-v-parameter-simulation=""></i></span>))}</div>) : ((variant === 'learning') ? (<div data-v-parameter-simulation="" className={cx("curve-simulation")}><span data-v-parameter-simulation="" style={{ '--curve-progress': `${clampedProgress()}%` } as CSSProperties} className={cx("curve-path")}></span>
        <span data-v-parameter-simulation="" style={{ left: `${Math.max(7, clampedProgress())}%` } as CSSProperties} className={cx("curve-dot")}></span></div>) : ((variant === 'subsample' || variant === 'features') ? (<div data-v-parameter-simulation="" className={cx("sample-simulation")}>{each(12).map(([_index, index]) => (<span data-v-parameter-simulation="" key={index} className={cx(['sample', { kept: index <= Math.max(1, Math.round((clampedProgress() / 100) * 12)) }])}></span>))}</div>) : ((variant === 'child-weight' || variant === 'regularization') ? (<div data-v-parameter-simulation="" className={cx("bar-simulation")}><span data-v-parameter-simulation="" className={cx("bar-track")}><span data-v-parameter-simulation="" style={{ width: `${Math.max(10, clampedProgress())}%` } as CSSProperties} className={cx("bar-fill")}></span></span>
        <span data-v-parameter-simulation="" className={cx("bar-caption")}></span></div>) : ((variant === 'split') ? (<div data-v-parameter-simulation="" className={cx("split-simulation")}><span data-v-parameter-simulation="" style={{ width: `${100 - clampedProgress()}%` } as CSSProperties} className={cx("split-train")}></span>
        <span data-v-parameter-simulation="" style={{ width: `${clampedProgress()}%` } as CSSProperties} className={cx("split-test")}></span></div>) : (<div data-v-parameter-simulation="" className={cx("seed-simulation")}>{each(5).map(([_index, index]) => (<span data-v-parameter-simulation="" key={index} className={cx(['seed-box', { active: index === 3 }])}>{display(index + 3)}</span>))}</div>))))))}</div></>);
}
