import type { ChangeEvent } from 'react';
import { useEvaluation } from "../../hooks/useEvaluation";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './Evaluation.module.css';
export default function Evaluation(input: {}) {
    const cx = bindStyles(styles);
    const { models, selectedModelId, modelState, evaluation, training, summaryCards, evaluationAvailable, isLoading, isStateLoading, error, selectModel, fetchModels, formatPercent, formatDate, formatAngle, formatTarget, } = useEvaluation();
    const confusionMatrix = (() => evaluation?.confusion_matrix ?? [])();
    const classDistribution = (() => Object.entries(evaluation?.test_class_distribution ?? {}))();
    const selectedDatasetNames = (() => training?.dataset_names ?? [])();
    const selectedFeatures = (() => modelState?.features.selected ?? [])();
    const featureWarnings = (() => modelState?.feature_warnings ?? [])();
    const handleModelChange = async (event: ChangeEvent<HTMLSelectElement>) => {
        const value = (event.target as HTMLSelectElement).value;
        const id = Number(value);
        if (Number.isInteger(id) && id > 0) {
            await selectModel(id);
        }
    };
    return (<><main {...scopeAttributes(input)} data-v-evaluation="" className={cx("evaluation-page")}><header data-v-evaluation="" className={cx("page-header")}><div data-v-evaluation=""><div data-v-evaluation="" className={cx("eyebrow")}><span data-v-evaluation="" className={cx("eyebrow-dot")}></span>
    {" VECTOFIT MODEL EVALUATION "}</div>
    <h1 data-v-evaluation="">{"Evaluation"}</h1>
    <p data-v-evaluation="">{" Review the held-out test performance of models registered by the training pipeline. "}</p></div>
    <button data-v-evaluation="" type="button" disabled={isLoading || isStateLoading} onClick={() => fetchModels()} className={cx("secondary-button")}>{display(isLoading ? "Refreshing…" : "Refresh results")}</button></header>
        {(error) ? (<div data-v-evaluation="" role="alert" className={cx("message error-message")}><strong data-v-evaluation="">{"Could not load evaluation data"}</strong>
        <p data-v-evaluation="">{display(error)}</p></div>) : (null)}
        {(isLoading && !models.length) ? (<section data-v-evaluation="" className={cx("panel loading-panel")}>{" Loading registered models… "}</section>) : ((!models.length && !isLoading) ? (<section data-v-evaluation="" className={cx("panel empty-panel")}><h2 data-v-evaluation="">{"No registered models yet"}</h2>
        <p data-v-evaluation="">{" Complete a training job first. Successfully registered models will appear here with their saved evaluation results. "}</p></section>) : (<><section data-v-evaluation="" className={cx("panel model-selector-panel")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Registered model"}</h2>
        <p data-v-evaluation="">{"Select a model to inspect its saved evaluation results."}</p></div>
        {(modelState) ? (<span data-v-evaluation="" className={cx("status-badge", { active: modelState.is_active })}>{display(modelState.is_active ? "ACTIVE FOR INFERENCE" : "REGISTERED")}</span>) : (null)}</div>
        <label data-v-evaluation="" htmlFor="evaluation-model" className={cx("field-label")}>{" Model "}</label>
        <select data-v-evaluation="" id="evaluation-model" value={selectedModelId ?? ''} disabled={isStateLoading} onChange={handleModelChange} className={cx("model-select")}>{each(models).map(([_index, model]) => (<option data-v-evaluation="" key={model.id} value={model.id}>{display(model.name)}
            {" · v"}
            {display(model.version)}
            {" · "}
            {display(formatTarget(model.prediction_target))}
            {" · "}
            {display(formatAngle(model.view_angle))}</option>))}</select>
        {(isStateLoading) ? (<p data-v-evaluation="" className={cx("muted loading-inline")}>{" Loading the selected model's evaluation state… "}</p>) : (null)}</section>
            {(modelState && !isStateLoading) ? (<><section data-v-evaluation="" className={cx("model-overview")}><div data-v-evaluation="" className={cx("model-title")}><div data-v-evaluation=""><div data-v-evaluation="" className={cx("model-kicker")}>{display(modelState.algorithm)}</div>
            <h2 data-v-evaluation="">{display(modelState.name)}</h2>
            <p data-v-evaluation="">{" Version "}
            {display(modelState.version)}
            {" · Training job #"}
            {display(modelState.training.job_id)}</p></div>
            <span data-v-evaluation="" className={cx("status-badge", { active: modelState.is_active })}>{display(modelState.is_active ? "ACTIVE" : "REGISTERED")}</span></div>
            <div data-v-evaluation="" className={cx("metadata-grid")}><div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Camera angle"}</span>
            <strong data-v-evaluation="">{display(formatAngle(modelState.view_angle))}</strong></div>
            <div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Prediction target"}</span>
            <strong data-v-evaluation="">{display(formatTarget(modelState.prediction_target))}</strong></div>
            <div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Feature schema"}</span>
            <strong data-v-evaluation="">{display(modelState.feature_schema_version || "—")}</strong></div>
            <div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Artifact"}</span>
            <strong data-v-evaluation="">{display(modelState.artifact_available ? "Available" : "Missing")}</strong></div>
            <div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Training status"}</span>
            <strong data-v-evaluation="">{display(training?.status ?? "—")}</strong></div>
            <div data-v-evaluation="" className={cx("metadata-item")}><span data-v-evaluation="">{"Created"}</span>
            <strong data-v-evaluation="">{display(formatDate(modelState.created_at))}</strong></div></div></section>
            <section data-v-evaluation="" className={cx("section-block")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Held-out test performance"}</h2>
            <p data-v-evaluation="">{" These are saved training-evaluation metrics, not scores from a live phone assessment. "}</p></div>
            <span data-v-evaluation="" className={cx("status-badge", { active: evaluationAvailable })}>{display(evaluationAvailable ? "RESULTS AVAILABLE" : "NO RESULTS")}</span></div>
                {(evaluationAvailable) ? (<div data-v-evaluation="" className={cx("metric-grid")}>{each(summaryCards).map(([_index, card]) => (<article data-v-evaluation="" key={card.label} className={cx("metric-card")}><span data-v-evaluation="" className={cx("metric-label")}>{display(card.label)}</span>
                    <strong data-v-evaluation="" className={cx("metric-value")}>{display(card.value)}</strong>
                    <p data-v-evaluation="">{display(card.description)}</p></article>))}</div>) : (<div data-v-evaluation="" className={cx("panel empty-panel")}><h3 data-v-evaluation="">{"Evaluation metrics unavailable"}</h3>
                <p data-v-evaluation="">{" This model does not have completed held-out evaluation results. Check the training job status and its saved metrics. "}</p></div>)}
                {(evaluation) ? (<div data-v-evaluation="" className={cx("secondary-metrics")}><div data-v-evaluation="" className={cx("secondary-metric")}><span data-v-evaluation="">{"Recall"}</span>
                <strong data-v-evaluation="">{display(formatPercent(evaluation.recall))}</strong></div>
                <div data-v-evaluation="" className={cx("secondary-metric")}><span data-v-evaluation="">{"Test samples"}</span>
                <strong data-v-evaluation="">{display(training?.test_count ?? "—")}</strong></div>
                <div data-v-evaluation="" className={cx("secondary-metric")}><span data-v-evaluation="">{"Training samples"}</span>
                <strong data-v-evaluation="">{display(training?.train_count ?? "—")}</strong></div>
                <div data-v-evaluation="" className={cx("secondary-metric")}><span data-v-evaluation="">{"Total samples"}</span>
                <strong data-v-evaluation="">{display(training?.sample_count ?? "—")}</strong></div></div>) : (null)}</section>
            <section data-v-evaluation="" className={cx("section-block")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Training data and split"}</h2>
            <p data-v-evaluation="">{" Dataset provenance and how the evaluation data was separated. "}</p></div></div>
            <div data-v-evaluation="" className={cx("panel details-panel")}><div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Datasets"}</span>
            {(selectedDatasetNames.length) ? (<div data-v-evaluation="" className={cx("chip-list")}>{each(selectedDatasetNames).map(([_index, name]) => (<span data-v-evaluation="" key={name} className={cx("data-chip")}>{display(name)}</span>))}</div>) : (<strong data-v-evaluation="">{"No dataset names recorded"}</strong>)}</div>
            <div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Split strategy"}</span>
            <strong data-v-evaluation="">{display(training?.split_strategy || "—")}</strong></div>
            <div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Test size"}</span>
            <strong data-v-evaluation="">{display(training?.test_size != null
                    ? formatPercent(training.test_size)
                    : "—")}</strong></div>
            <div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Random seed"}</span>
            <strong data-v-evaluation="">{display(training?.random_seed ?? "—")}</strong></div>
            <div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Completed at"}</span>
            <strong data-v-evaluation="">{display(formatDate(training?.completed_at))}</strong></div>
            <div data-v-evaluation="" className={cx("detail-row")}><span data-v-evaluation="">{"Selected features"}</span>
            {(selectedFeatures.length) ? (<div data-v-evaluation="" className={cx("chip-list")}>{each(selectedFeatures).map(([_index, feature]) => (<span data-v-evaluation="" key={feature} className={cx("data-chip")}>{display(feature)}</span>))}</div>) : (<strong data-v-evaluation="">{"No selected features recorded"}</strong>)}</div></div></section>
            <section data-v-evaluation="" className={cx("section-block")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Confusion matrix"}</h2>
            <p data-v-evaluation="">{" Rows and columns follow the classifier's class order. Values come from the saved held-out test evaluation. "}</p></div></div>
                {(confusionMatrix.length) ? (<div data-v-evaluation="" className={cx("panel matrix-panel")}><div data-v-evaluation="" className={cx("matrix-scroll")}><table data-v-evaluation="" className={cx("matrix-table")}><caption data-v-evaluation="">{" Actual classes by predicted classes "}</caption>
                <thead data-v-evaluation=""><tr data-v-evaluation=""><th data-v-evaluation="" scope="col">{"Actual \\ Predicted"}</th>
                    {each(confusionMatrix[0]).map(([index, _]) => (<th data-v-evaluation="" key={`predicted-${index}`} scope="col">{" Class "}
                    {display(index)}</th>))}</tr></thead>
                <tbody data-v-evaluation="">{each(confusionMatrix).map(([rowIndex, row]) => (<tr data-v-evaluation="" key={`actual-${rowIndex}`}><th data-v-evaluation="" scope="row">{"Class "}
                    {display(rowIndex)}</th>
                    {each(row).map(([colIndex, value]) => (<td data-v-evaluation="" key={colIndex}>{display(value)}</td>))}</tr>))}</tbody></table></div>
                <p data-v-evaluation="" className={cx("muted matrix-note")}>{" Class names are shown as indices because the state response does not expose an explicit class-label ordering in this table. "}</p></div>) : (<div data-v-evaluation="" className={cx("panel empty-panel")}>{" No confusion matrix is available for this model. "}</div>)}</section>
                {(classDistribution.length) ? (<section data-v-evaluation="" className={cx("section-block")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Test-set class distribution"}</h2>
                <p data-v-evaluation="">{" Number of samples in each class used for held-out evaluation. "}</p></div></div>
                <div data-v-evaluation="" className={cx("panel details-panel")}>{each(classDistribution).map(([_index, [label, count]]) => (<div data-v-evaluation="" key={label} className={cx("detail-row")}><span data-v-evaluation="">{display(label)}</span>
                    <strong data-v-evaluation="">{display(count)}</strong></div>))}</div></section>) : (null)}
                {(featureWarnings.length) ? (<section data-v-evaluation="" className={cx("section-block")}><div data-v-evaluation="" className={cx("section-heading")}><div data-v-evaluation=""><h2 data-v-evaluation="">{"Feature warnings"}</h2>
                <p data-v-evaluation="">{"Warnings returned by the registered model's state endpoint."}</p></div></div>
                <div data-v-evaluation="" className={cx("message warning-message")}><ul data-v-evaluation="">{each(featureWarnings).map(([_index, warning]) => (<li data-v-evaluation="" key={warning}>{display(warning)}</li>))}</ul></div></section>) : (null)}</>) : (null)}</>))}</main></>);
}
