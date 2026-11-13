import type { ModelCard } from "../../services/modelService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './ModelCard.module.css';
export default function ModelCard(input: {
    card: ModelCard;
}) {
    const props = { ...{}, ...input };
    const { card } = props;
    const cx = bindStyles(styles);
    const statusLabel = (() => {
        switch (props.card.status) {
            case "ready":
                return "READY FOR ACTIVATION";
            case "warning":
                return "READY WITH WARNINGS";
            case "blocked":
                return "ACTIVATION BLOCKED";
            default:
                return String(props.card.status).toUpperCase();
        }
    })();
    const targetLabel = (() => {
        return props.card.prediction_target === "knee_alignment"
            ? "Frontal-plane knee alignment"
            : "Unsupported model setup";
    })();
    const classLabels = (() => Object.entries(props.card.class_mapping)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([index, label]) => ({ index, label })))();
    const originEntries = (() => Object.entries(props.card.data_provenance.label_origin_counts).sort(([a], [b]) => a.localeCompare(b)))();
    const shortHash = (() => {
        const hash = props.card.generated_from.manifest_sha256;
        return hash ? `${hash.slice(0, 12)}…` : "not recorded";
    })();
    const checkStatusLabel = (status: string) => {
        if (status === "pass")
            return "Pass";
        if (status === "warn")
            return "Warning";
        return "Blocked";
    };
    return (<><section {...scopeAttributes(input)} data-v-model-card="" className={cx("content-card model-card")}><div data-v-model-card="" className={cx("section-header")}><div data-v-model-card="" className={cx("section-title-row")}><div data-v-model-card="" className={cx("section-marker")}></div>
    <div data-v-model-card=""><h2 data-v-model-card="">{"Model Card & Activation Readiness"}</h2>
    <p data-v-model-card="">{" Evidence recorded with this version. Activation is gated by the checks below. "}</p></div></div>
    <span data-v-model-card="" className={cx("card-status", card.status)}>{display(statusLabel)}</span></div>
    <div data-v-model-card="" className={cx("card-body")}><p data-v-model-card="" className={cx("readiness-summary")}><strong data-v-model-card="">{display(card.activation.allowed ? "Eligible" : "Not eligible")}
    {" for inference "}</strong>
    {" — "}
    {display(card.summary.passed_checks)}
    {" of "}
    {display(card.summary.total_checks)}
    {" checks pass, "}
    {display(card.summary.warning_checks)}
    {" warning(s), "}
    {display(card.summary.failed_checks)}
    {" blocker(s). "}</p>
        {(card.activation.blockers.length) ? (<div data-v-model-card="" className={cx("blocker-panel")}><strong data-v-model-card="">{"Resolve these before activating"}</strong>
        <ul data-v-model-card="">{each(card.activation.blockers).map(([_index, blocker]) => (<li data-v-model-card="" key={blocker.code}><span data-v-model-card="">{display(blocker.detail)}</span>
            {(blocker.remediation) ? (<small data-v-model-card="">{display(blocker.remediation)}</small>) : (null)}</li>))}</ul></div>) : (null)}
    <div data-v-model-card="" className={cx("metadata-strip")}><div data-v-model-card=""><span data-v-model-card="">{"Prediction target"}</span>
    <strong data-v-model-card="">{display(targetLabel)}</strong></div>
    <div data-v-model-card=""><span data-v-model-card="">{"Camera angle"}</span>
    <strong data-v-model-card="">{display(card.view_angle || "not recorded")}</strong></div>
    <div data-v-model-card=""><span data-v-model-card="">{"Held-out test samples"}</span>
    <strong data-v-model-card="">{display(card.held_out_test_count)}</strong></div>
    <div data-v-model-card=""><span data-v-model-card="">{"Participants in manifest"}</span>
    <strong data-v-model-card="">{display(card.data_provenance.participant_count)}</strong></div>
    <div data-v-model-card=""><span data-v-model-card="">{"Manifest hash"}</span>
    <strong data-v-model-card="" title={card.generated_from.manifest_sha256 ?? ''}>{display(shortHash)}</strong></div>
    <div data-v-model-card=""><span data-v-model-card="">{"Evaluation scope"}</span>
    <strong data-v-model-card="">{display(card.evaluation_scope.replaceAll("_", " "))}</strong></div></div>
    <div data-v-model-card="" className={cx("card-columns")}><div data-v-model-card=""><h3 data-v-model-card="">{"Checks"}</h3>
    <ul data-v-model-card="" className={cx("check-list")}>{each(card.checks).map(([_index, check]) => (<li data-v-model-card="" key={check.code} className={cx("check-row")}><span data-v-model-card="" aria-hidden="true" className={cx("check-indicator", check.status)}>{display(check.status === "pass" ? "✓" : check.status === "warn" ? "!" : "×")}</span>
        <div data-v-model-card=""><strong data-v-model-card="">{display(check.label)}
        {" "}
        <small data-v-model-card="" className={cx("check-status-text", check.status)}>{display(checkStatusLabel(check.status))}</small></strong>
        <p data-v-model-card="">{display(check.detail)}</p>
        {(check.remediation && check.status !== 'pass') ? (<p data-v-model-card="" className={cx("remediation")}>{display(check.remediation)}</p>) : (null)}</div></li>))}</ul></div>
    <div data-v-model-card="" className={cx("side-column")}><h3 data-v-model-card="">{"Class labels"}</h3>
        {(classLabels.length) ? (<div data-v-model-card="" className={cx("class-labels")}>{each(classLabels).map(([_index, entry]) => (<span data-v-model-card="" key={entry.index} className={cx("class-chip")}><small data-v-model-card="">{display(entry.index)}</small>
            {" "}
            {display(entry.label)}</span>))}</div>) : (<p data-v-model-card="" className={cx("muted-note")}>{" No explicit class ordering was recorded for this model. "}</p>)}
    <h3 data-v-model-card="">{"Label provenance"}</h3>
        {(originEntries.length) ? (<div data-v-model-card="" className={cx("origin-list")}>{each(originEntries).map(([_index, [origin, count]]) => (<div data-v-model-card="" key={origin}><span data-v-model-card="">{display(origin.replaceAll("_", " "))}</span>
            <strong data-v-model-card="">{display(count)}</strong></div>))}</div>) : (<p data-v-model-card="" className={cx("muted-note")}>{" The manifest has no per-sample label-origin records. "}</p>)}</div></div></div></section></>);
}
