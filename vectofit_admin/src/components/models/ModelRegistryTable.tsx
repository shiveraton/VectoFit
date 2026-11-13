import type { ModelRegistryRecord } from "../../services/modelService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './ModelRegistryTable.module.css';
type Callbacks = {
    onSelect?: (id: number) => void;
};
export default function ModelRegistryTable(input: {
    models: ModelRegistryRecord[];
    selectedModelId: number | null;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { models, selectedModelId } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "select", id: number): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "select":
            props.onSelect?.(...args as [
                id: number
            ]);
            break;
    } }) as Emit;
    const accuracy = (model: ModelRegistryRecord) => {
        const value = model.metrics?.accuracy;
        return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—";
    };
    const formatDate = (value: string) => new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
    }).format(new Date(value));
    return (<><div {...scopeAttributes(input)} data-v-model-registry-table="" className={cx("table-wrap")}><table data-v-model-registry-table=""><thead data-v-model-registry-table=""><tr data-v-model-registry-table=""><th data-v-model-registry-table="" scope="col">{"VERSION"}</th>
    <th data-v-model-registry-table="" scope="col">{"FPPA TARGET"}</th>
    <th data-v-model-registry-table="" scope="col">{"HELD-OUT ACCURACY"}</th>
    <th data-v-model-registry-table="" scope="col">{"TRAINING JOB"}</th>
    <th data-v-model-registry-table="" scope="col">{"STATUS"}</th>
    <th data-v-model-registry-table="" scope="col">{"CREATED"}</th></tr></thead>
    <tbody data-v-model-registry-table="">{each(models).map(([_index, model]) => (<tr data-v-model-registry-table="" key={model.id} onClick={() => { emit('select', model.id); }} className={cx({
                selected: model.id === selectedModelId,
            })}><td data-v-model-registry-table="" className={cx("version-cell")}><button data-v-model-registry-table="" type="button" aria-pressed={model.id === selectedModelId} aria-label={`Inspect ${model.name}, version ${model.version}`} onClick={(event) => { event.stopPropagation(); emit('select', model.id); }} className={cx("version-select")}>{"v"}
        {display(model.version)}</button>
        <span data-v-model-registry-table="">{display(model.name)}</span></td>
        <td data-v-model-registry-table="">{" Good / bad knee alignment "}</td>
        <td data-v-model-registry-table="" className={cx("numeric")}>{display(accuracy(model))}</td>
        <td data-v-model-registry-table="" className={cx("numeric")}>{"#"}
        {display(model.training_job)}</td>
        <td data-v-model-registry-table=""><span data-v-model-registry-table="" className={cx("status", { active: model.is_active })}>{display(model.is_active ? "ACTIVE" : "REGISTERED")}</span></td>
        <td data-v-model-registry-table="">{display(formatDate(model.created_at))}</td></tr>))}</tbody></table></div></>);
}
