import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './StructureGrid.module.css';
export interface StructureItem {
    id: string;
    icon: string;
    iconVariant: 'feature' | 'target' | 'error' | 'sample';
    title: string;
    value: string;
}
export default function StructureGrid(input: {
    items?: StructureItem[];
}) {
    const props = { ...{
            items: [
                {
                    id: 'features',
                    icon: 'F',
                    iconVariant: 'feature',
                    title: 'Features',
                    value: 'ROM, asymmetry, angles, velocity'
                },
                {
                    id: 'primary-target',
                    icon: 'C',
                    iconVariant: 'target',
                    title: 'Primary Target',
                    value: 'Correct / Incorrect'
                },
                {
                    id: 'secondary-target',
                    icon: 'E',
                    iconVariant: 'error',
                    title: 'Secondary Targets',
                    value: 'Biomechanical error labels'
                },
                {
                    id: 'sample-unit',
                    icon: 'R',
                    iconVariant: 'sample',
                    title: 'Sample Unit',
                    value: 'One completed squat repetition'
                }
            ]
        }, ...input };
    const { items } = props;
    const cx = bindStyles(styles);
    return (<><div {...scopeAttributes(input)} data-v-structure-grid="" className={cx("structure-grid")}>{each(items).map(([_index, item]) => (<div data-v-structure-grid="" key={item.id} className={cx("structure-item")}><div data-v-structure-grid="" className={cx("structure-content")}><span data-v-structure-grid="" className={cx("structure-title")}>{display(item.title)}</span>
        <span data-v-structure-grid="" className={cx("structure-value")}>{display(item.value)}</span></div></div>))}</div></>);
}
