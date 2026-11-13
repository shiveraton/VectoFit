import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../query';
import { pilotResultsService, type PilotMetricResult, type PilotResults, } from "../../services/pilotResultsService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './PilotResults.module.css';
export default function PilotResults(input: {}) {
    const cx = bindStyles(styles);
    const query = useQuery({ queryKey: queryKeys.pilot, queryFn: pilotResultsService.getResults });
    const results: PilotResults | null = query.data ?? null;
    const error = query.error ? 'No pilot results are available. Run run_m0_m1 first.' : null;
    const isLoading = query.isFetching;
    const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
    const formatInterval = (value: number) => `${value.toFixed(3)}`;
    const loadResults = () => query.refetch();
    const participantRows = (result: PilotMetricResult) => result.per_participant;
    return (<><div {...scopeAttributes(input)} data-v-pilot-results="" className={cx("pilot-page")}><header data-v-pilot-results="" className={cx("page-header")}><div data-v-pilot-results=""><div data-v-pilot-results="" className={cx("eyebrow")}>{"VECTOFIT EXPLORATORY PILOT"}</div>
    <h1 data-v-pilot-results="">{"M0 / M1 Results"}</h1>
    <p data-v-pilot-results="">{"LOPO comparison of four-feature XGBoost M0 and six-feature XGBoost M1. The threshold rule is reported separately."}</p></div>
    <button data-v-pilot-results="" type="button" disabled={isLoading} onClick={() => loadResults()} className={cx("secondary-button")}>{display(isLoading ? "Loading…" : "Refresh")}</button></header>
        {(error) ? (<section data-v-pilot-results="" role="alert" className={cx("panel message")}>{display(error)}</section>) : ((isLoading) ? (<section data-v-pilot-results="" className={cx("panel")}>{"Loading pilot results…"}</section>) : ((results) ? (<><section data-v-pilot-results="" className={cx("panel metadata")}><strong data-v-pilot-results="">{display(results.label)}</strong>
        <span data-v-pilot-results="">{"Feature schema: "}
        {display(results.feature_schema_version)}</span>
        <span data-v-pilot-results="">{"Participants: "}
        {display(results.M0.per_participant.length)}</span>
        <span data-v-pilot-results="">{"Samples: "}
        {display(results.M0.oof_predictions?.length ?? "n/a")}</span>
        <span data-v-pilot-results="">{"Exploratory pilot; LOPO estimates are not a validated clinical model."}</span>
        <span data-v-pilot-results="">{"Delta M1 − M0: "}
        {display(formatPercent(results.delta_macro_f1))}</span>
        <span data-v-pilot-results="">{" Bootstrap 95% interval: ["}
        {display(formatInterval(results.delta_macro_f1_bootstrap_95.lower))}
        {", "}
        {display(formatInterval(results.delta_macro_f1_bootstrap_95.upper))}
        {"] "}</span></section>
        <section data-v-pilot-results="" className={cx("panel")}><h2 data-v-pilot-results="">{"LOPO model comparison"}</h2>
        <table data-v-pilot-results=""><thead data-v-pilot-results=""><tr data-v-pilot-results=""><th data-v-pilot-results="">{"Model"}</th>
        <th data-v-pilot-results="">{"Features"}</th>
        <th data-v-pilot-results="">{"Macro-F1"}</th>
        <th data-v-pilot-results="">{"Participants"}</th></tr></thead>
        <tbody data-v-pilot-results=""><tr data-v-pilot-results=""><td data-v-pilot-results="">{"M0"}</td>
        <td data-v-pilot-results="">{display(results.M0_features.join(", "))}</td>
        <td data-v-pilot-results="">{display(formatPercent(results.M0.macro_f1))}</td>
        <td data-v-pilot-results="">{display(results.M0.per_participant.length)}</td></tr>
        <tr data-v-pilot-results=""><td data-v-pilot-results="">{"M1"}</td>
        <td data-v-pilot-results="">{display(results.M1_features.join(", "))}</td>
        <td data-v-pilot-results="">{display(formatPercent(results.M1.macro_f1))}</td>
        <td data-v-pilot-results="">{display(results.M1.per_participant.length)}</td></tr></tbody></table></section>
        <section data-v-pilot-results="" className={cx("panel")}><h2 data-v-pilot-results="">{"Fixed threshold baseline"}</h2>
        <p data-v-pilot-results="">{display(results.threshold_rule_baseline.rule)}</p>
        <table data-v-pilot-results=""><thead data-v-pilot-results=""><tr data-v-pilot-results=""><th data-v-pilot-results="">{"Run"}</th>
        <th data-v-pilot-results="">{"Cutoff"}</th>
        <th data-v-pilot-results="">{"Macro-F1"}</th>
        <th data-v-pilot-results="">{"Confusion matrix"}</th></tr></thead>
        <tbody data-v-pilot-results=""><tr data-v-pilot-results=""><td data-v-pilot-results="">{display(results.threshold_rule_baseline.primary.label)}</td>
        <td data-v-pilot-results="">{display(results.threshold_rule_baseline.primary.cutoff_degrees.valgus)}
        {"° / "}
        {display(results.threshold_rule_baseline.primary.cutoff_degrees.varus)}
        {"°"}</td>
        <td data-v-pilot-results="">{display(formatPercent(results.threshold_rule_baseline.primary.macro_f1))}</td>
        <td data-v-pilot-results="">{display(results.threshold_rule_baseline.primary.confusion_matrix.join(" / "))}</td></tr>
            {each(results.threshold_rule_baseline.sensitivity).map(([_index, run]) => (<tr data-v-pilot-results="" key={run.cutoff_degrees.valgus}><td data-v-pilot-results="">{display(run.label)}</td>
            <td data-v-pilot-results="">{display(run.cutoff_degrees.valgus)}
            {"° / "}
            {display(run.cutoff_degrees.varus)}
            {"°"}</td>
            <td data-v-pilot-results="">{display(formatPercent(run.macro_f1))}</td>
            <td data-v-pilot-results="">{display(run.confusion_matrix.join(" / "))}</td></tr>))}</tbody></table></section>
        <section data-v-pilot-results="" className={cx("panel")}><h2 data-v-pilot-results="">{"Per-participant LOPO macro-F1"}</h2>
        <table data-v-pilot-results=""><thead data-v-pilot-results=""><tr data-v-pilot-results=""><th data-v-pilot-results="">{"Participant"}</th>
        <th data-v-pilot-results="">{"M0"}</th>
        <th data-v-pilot-results="">{"M1"}</th>
        <th data-v-pilot-results="">{"Samples"}</th></tr></thead>
        <tbody data-v-pilot-results="">{each(participantRows(results.M0)).map(([_index, row]) => (<tr data-v-pilot-results="" key={row.participant}><td data-v-pilot-results="">{display(row.participant)}</td>
            <td data-v-pilot-results="">{display(formatPercent(row.macro_f1))}</td>
            <td data-v-pilot-results="">{display(formatPercent(results.M1.per_participant.find((item) => item.participant === row.participant)?.macro_f1 ?? 0))}</td>
            <td data-v-pilot-results="">{display(row.sample_count)}</td></tr>))}</tbody></table></section></>) : (null)))}</div></>);
}
