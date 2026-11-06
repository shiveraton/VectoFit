import { useState } from 'react';
import { Link } from 'react-router';
import { useDashboard } from "../../hooks/useDashboard";
import SummaryCard from "../../components/datasets/SummaryCard";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './Dashboard.module.css';
interface Props {
    eyebrowText?: string;
    pageTitle?: string;
    pageDescription?: string;
}
export default function Dashboard(input: Props) {
    const props = { ...{
            eyebrowText: "VECTOFIT SYSTEM OVERVIEW",
            pageTitle: "Dashboard",
            pageDescription: "Datasets, model versions, and training activity in one research workspace.",
        }, ...input };
    const { eyebrowText, pageTitle, pageDescription } = props;
    const cx = bindStyles(styles);
    const { isLoading: dashboardLoading, dashboardCards, currentModel, error, fetchAllDashboardData } = useDashboard();
    const [refreshRequested, setIsRefreshing] = useState(false);
    const isRefreshing = refreshRequested || dashboardLoading;
    const handleRefresh = async (force = true) => {
        if (isRefreshing)
            return;
        setIsRefreshing(true);
        try {
            await fetchAllDashboardData(force);
        }
        finally {
            setIsRefreshing(false);
        }
    };
    const formatMetric = (value: unknown, options?: {
        multiplier?: number;
        suffix?: string;
        decimals?: number;
    }): string => {
        if (typeof value !== "number" || !Number.isFinite(value)) {
            return "N/A";
        }
        const { multiplier = 1, suffix = "", decimals = 1 } = options ?? {};
        return `${(value * multiplier).toFixed(decimals)}${suffix}`;
    };
    const modelAlgorithm = (() => currentModel?.algorithm ?? "N/A")();
    const modelLatency = (() => formatMetric(currentModel?.metrics?.latencyMs, {
        suffix: " ms",
        decimals: 1,
    }))();
    const modelAccuracy = (() => formatMetric(currentModel?.metrics?.accuracy, {
        multiplier: 100,
        suffix: "%",
        decimals: 1,
    }))();
    return (<><div {...scopeAttributes(input)} data-v-dashboard="" className={cx("dashboard-page")}><header data-v-dashboard="" className={cx("page-header")}><div data-v-dashboard="" className={cx("page-heading")}><div data-v-dashboard="" className={cx("eyebrow")}><span data-v-dashboard="" className={cx("eyebrow-dot")}></span>
    {" "}
    {display(eyebrowText)}</div>
    <h1 data-v-dashboard="">{display(pageTitle)}</h1>
    <p data-v-dashboard="">{display(pageDescription)}</p></div>
    <button data-v-dashboard="" disabled={isRefreshing} onClick={() => { handleRefresh(true); }} className={cx("secondary-button")}><span data-v-dashboard="" aria-hidden="true" className={cx("button-icon")}>{"↻"}</span>
    {" "}
    {display(isRefreshing ? "Refreshing..." : "Refresh overview")}</button></header>
    {(isRefreshing) ? (<p data-v-dashboard="" role="status" className={cx("refresh-status")}>{"Updating workspace overview..."}</p>) : (null)}
        {(error) ? (<div data-v-dashboard="" role="alert" className={cx("error-banner")}><strong data-v-dashboard="">{"Workspace data could not be fully loaded."}</strong>
        {" "}
        {display(error)}
        {" Refresh to try again."}</div>) : (<section data-v-dashboard="" aria-busy={isRefreshing} className={cx("summary-grid")}>{each(dashboardCards).map(([_index, card]) => (<SummaryCard data-v-dashboard="" key={card.label} {...card}></SummaryCard>))}</section>)}
        {(!error) ? (<section data-v-dashboard="" className={cx("content-card")}><div data-v-dashboard="" className={cx("section-header")}><div data-v-dashboard="" className={cx("section-title-row")}><div data-v-dashboard="" className={cx("section-marker")}></div>
        <div data-v-dashboard=""><h2 data-v-dashboard="">{"Registered Model Overview"}</h2>
        <p data-v-dashboard="">{"Model metadata and available performance metrics."}</p></div></div>
        <span data-v-dashboard="" className={cx("status-badge", { 'is-active': currentModel })}>{display(currentModel ? "REGISTERED" : "NO MODEL")}</span></div>
        <div data-v-dashboard="" className={cx("card-body")}>{(currentModel) ? (<><div data-v-dashboard="" className={cx("active-endpoint-details")}><div data-v-dashboard="" className={cx("detail-group")}><span data-v-dashboard="" className={cx("detail-label")}>{"Model Name"}</span>
            <span data-v-dashboard="" className={cx("detail-value")}>{display(currentModel.name)}</span></div>
            <div data-v-dashboard="" className={cx("detail-group")}><span data-v-dashboard="" className={cx("detail-label")}>{"Version"}</span>
            <span data-v-dashboard="" className={cx("detail-value font-mono")}>{display(currentModel.version)}</span></div>
            <div data-v-dashboard="" className={cx("detail-group")}><span data-v-dashboard="" className={cx("detail-label")}>{"Algorithm"}</span>
            <span data-v-dashboard="" className={cx("detail-value")}>{display(modelAlgorithm)}</span></div>
            <div data-v-dashboard="" className={cx("detail-group")}><span data-v-dashboard="" className={cx("detail-label")}>{"p99 Latency"}</span>
            <span data-v-dashboard="" className={cx("detail-value font-mono")}>{display(modelLatency)}</span></div>
            <div data-v-dashboard="" className={cx("detail-group")}><span data-v-dashboard="" className={cx("detail-label")}>{"Accuracy"}</span>
            <span data-v-dashboard="" className={cx("detail-value font-mono")}>{display(modelAccuracy)}</span></div></div></>) : (<><div data-v-dashboard="" className={cx("empty-endpoint")}><h3 data-v-dashboard="">{"No registered model yet"}</h3>
            <p data-v-dashboard="">{"Complete a training run, then inspect its evidence in the model registry."}</p>
            <Link data-v-dashboard="" to="/training" className={cx("secondary-button")}>{"Go to training"}</Link></div></>)}</div></section>) : (null)}
    <section data-v-dashboard="" aria-labelledby="workspace-tasks-title" className={cx("workspace-tasks")}><div data-v-dashboard="" className={cx("tasks-heading")}><h2 data-v-dashboard="" id="workspace-tasks-title">{"Research workflow"}</h2>
    <p data-v-dashboard="">{"Move from source data to reviewed model evidence."}</p></div>
    <Link data-v-dashboard="" to="/dataset" className={cx("task-link")}><span data-v-dashboard="" className={cx("task-number")}>{"01"}</span>
    <div data-v-dashboard=""><strong data-v-dashboard="">{"Prepare your datasets"}</strong>
    <p data-v-dashboard="">{"Import recordings, review labels, and check training readiness."}</p></div>
    <span data-v-dashboard="" aria-hidden="true">{"→"}</span></Link>
    <Link data-v-dashboard="" to="/training" className={cx("task-link")}><span data-v-dashboard="" className={cx("task-number")}>{"02"}</span>
    <div data-v-dashboard=""><strong data-v-dashboard="">{"Configure a training run"}</strong>
    <p data-v-dashboard="">{"Choose eligible datasets and inspect the FPPA v2 configuration."}</p></div>
    <span data-v-dashboard="" aria-hidden="true">{"→"}</span></Link>
    <Link data-v-dashboard="" to="/models" className={cx("task-link")}><span data-v-dashboard="" className={cx("task-number")}>{"03"}</span>
    <div data-v-dashboard=""><strong data-v-dashboard="">{"Review model evidence"}</strong>
    <p data-v-dashboard="">{"Compare saved versions, evaluation results, and activation checks."}</p></div>
    <span data-v-dashboard="" aria-hidden="true">{"→"}</span></Link></section></div></>);
}
