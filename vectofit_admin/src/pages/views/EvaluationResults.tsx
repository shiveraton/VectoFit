import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../query';
import { evaluationResultsService, type EvaluationMetricResult, type EvaluationResults, } from "../../services/evaluationResultsService";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './EvaluationResults.module.css';
export default function EvaluationResults(input: {}) {
    const cx = bindStyles(styles);
    const query = useQuery({ queryKey: queryKeys.evaluationResults, queryFn: evaluationResultsService.getResults });
    const results: EvaluationResults | null = query.data ?? null;
    const error = query.error ? 'Unable to load evaluation results. Try refreshing the page.' : null;
    const isLoading = query.isFetching;
    const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
    const formatInterval = (value: number) => `${value.toFixed(3)}`;
    const loadResults = () => query.refetch();
    const participantRows = (result: EvaluationMetricResult) => result.per_participant;
    return (<><div {...scopeAttributes(input)} data-v-evaluation-results="" className={cx("evaluation-results-page")}><header data-v-evaluation-results="" className={cx("page-header")}><div data-v-evaluation-results=""><div data-v-evaluation-results="" className={cx("eyebrow")}>{"VECTOFIT MODEL EVALUATION"}</div>
    <h1 data-v-evaluation-results="">{"Evaluation Results"}</h1>
    <p data-v-evaluation-results="">{"LOPO comparison of four-feature XGBoost M0 and six-feature XGBoost M1. The threshold rule is reported separately."}</p></div>
    <button data-v-evaluation-results="" type="button" disabled={isLoading} onClick={() => loadResults()} className={cx("secondary-button")}>{display(isLoading ? "Loading…" : "Refresh")}</button></header>
        {(error) ? (<section data-v-evaluation-results="" role="alert" className={cx("panel message")}>{display(error)}</section>) : ((isLoading) ? (<section data-v-evaluation-results="" className={cx("panel")}>{"Loading evaluation results…"}</section>) : ((results) ? (<><section data-v-evaluation-results="" className={cx("panel metadata")}><strong data-v-evaluation-results="">{"M0 / M1 evaluation"}</strong>
        <span data-v-evaluation-results="">{"Feature schema: "}
        {display(results.feature_schema_version)}</span>
        <span data-v-evaluation-results="">{"Participants: "}
        {display(results.M0.per_participant.length)}</span>
        <span data-v-evaluation-results="">{"Samples: "}
        {display(results.M0.oof_predictions?.length ?? "n/a")}</span>
        <span data-v-evaluation-results="">{"Exploratory evaluation; LOPO estimates do not establish clinical validity."}</span>
        <span data-v-evaluation-results="">{"Delta M1 − M0: "}
        {display(formatPercent(results.delta_macro_f1))}</span>
        <span data-v-evaluation-results="">{" Bootstrap 95% interval: ["}
        {display(formatInterval(results.delta_macro_f1_bootstrap_95.lower))}
        {", "}
        {display(formatInterval(results.delta_macro_f1_bootstrap_95.upper))}
        {"] "}</span></section>
        <section data-v-evaluation-results="" className={cx("panel")}><h2 data-v-evaluation-results="">{"LOPO model comparison"}</h2>
        <table data-v-evaluation-results=""><thead data-v-evaluation-results=""><tr data-v-evaluation-results=""><th data-v-evaluation-results="">{"Model"}</th>
        <th data-v-evaluation-results="">{"Features"}</th>
        <th data-v-evaluation-results="">{"Macro-F1"}</th>
        <th data-v-evaluation-results="">{"Participants"}</th></tr></thead>
        <tbody data-v-evaluation-results=""><tr data-v-evaluation-results=""><td data-v-evaluation-results="">{"M0"}</td>
        <td data-v-evaluation-results="">{display(results.M0_features.join(", "))}</td>
        <td data-v-evaluation-results="">{display(formatPercent(results.M0.macro_f1))}</td>
        <td data-v-evaluation-results="">{display(results.M0.per_participant.length)}</td></tr>
        <tr data-v-evaluation-results=""><td data-v-evaluation-results="">{"M1"}</td>
        <td data-v-evaluation-results="">{display(results.M1_features.join(", "))}</td>
        <td data-v-evaluation-results="">{display(formatPercent(results.M1.macro_f1))}</td>
        <td data-v-evaluation-results="">{display(results.M1.per_participant.length)}</td></tr></tbody></table></section>
        <section data-v-evaluation-results="" className={cx("panel")}><h2 data-v-evaluation-results="">{"Fixed threshold baseline"}</h2>
        <p data-v-evaluation-results="">{display(results.threshold_rule_baseline.rule)}</p>
        <table data-v-evaluation-results=""><thead data-v-evaluation-results=""><tr data-v-evaluation-results=""><th data-v-evaluation-results="">{"Run"}</th>
        <th data-v-evaluation-results="">{"Cutoff"}</th>
        <th data-v-evaluation-results="">{"Macro-F1"}</th>
        <th data-v-evaluation-results="">{"Confusion matrix"}</th></tr></thead>
        <tbody data-v-evaluation-results=""><tr data-v-evaluation-results=""><td data-v-evaluation-results="">{display(results.threshold_rule_baseline.primary.label)}</td>
        <td data-v-evaluation-results="">{display(results.threshold_rule_baseline.primary.cutoff_degrees.valgus)}
        {"° / "}
        {display(results.threshold_rule_baseline.primary.cutoff_degrees.varus)}
        {"°"}</td>
        <td data-v-evaluation-results="">{display(formatPercent(results.threshold_rule_baseline.primary.macro_f1))}</td>
        <td data-v-evaluation-results="">{display(results.threshold_rule_baseline.primary.confusion_matrix.join(" / "))}</td></tr>
            {each(results.threshold_rule_baseline.sensitivity).map(([_index, run]) => (<tr data-v-evaluation-results="" key={run.cutoff_degrees.valgus}><td data-v-evaluation-results="">{display(run.label)}</td>
            <td data-v-evaluation-results="">{display(run.cutoff_degrees.valgus)}
            {"° / "}
            {display(run.cutoff_degrees.varus)}
            {"°"}</td>
            <td data-v-evaluation-results="">{display(formatPercent(run.macro_f1))}</td>
            <td data-v-evaluation-results="">{display(run.confusion_matrix.join(" / "))}</td></tr>))}</tbody></table></section>
        <section data-v-evaluation-results="" className={cx("panel")}><h2 data-v-evaluation-results="">{"Per-participant LOPO macro-F1"}</h2>
        <table data-v-evaluation-results=""><thead data-v-evaluation-results=""><tr data-v-evaluation-results=""><th data-v-evaluation-results="">{"Participant"}</th>
        <th data-v-evaluation-results="">{"M0"}</th>
        <th data-v-evaluation-results="">{"M1"}</th>
        <th data-v-evaluation-results="">{"Samples"}</th></tr></thead>
        <tbody data-v-evaluation-results="">{each(participantRows(results.M0)).map(([_index, row]) => (<tr data-v-evaluation-results="" key={row.participant}><td data-v-evaluation-results="">{display(row.participant)}</td>
            <td data-v-evaluation-results="">{display(formatPercent(row.macro_f1))}</td>
            <td data-v-evaluation-results="">{display(formatPercent(results.M1.per_participant.find((item) => item.participant === row.participant)?.macro_f1 ?? 0))}</td>
            <td data-v-evaluation-results="">{display(row.sample_count)}</td></tr>))}</tbody></table></section></>) : (null)))}</div></>);
}
