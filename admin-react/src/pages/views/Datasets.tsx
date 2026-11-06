import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useDatasets } from "../../hooks/useDatasets";
import { useParticipants } from "../../hooks/useParticipants";
import { useAnnotationPool } from "../../hooks/useAnnotationPool";
import { VIEW_ANGLE_BY_ID, type Dataset } from "../../services/datasetService";
import SummaryCard from "../../components/datasets/SummaryCard";
import DatasetEmptyState from "../../components/datasets/DatasetEmptyState";
import StructureGrid from "../../components/datasets/StructureGrid";
import CreateDatasetModal from "../../components/datasets/CreateDatasetModal";
import DatasetImportModal from "../../components/datasets/DatasetImportModal";
import { bindStyles, each, display, scopeAttributes } from '../../presentation';
import styles from './Datasets.module.css';
type DatasetReviewMetrics = {
    human_reviewed_sample_count?: number | null;
    review_selected_sample_count?: number | null;
    pending_review_sample_count?: number | null;
};
export default function Datasets(input: {}) {
    const cx = bindStyles(styles);
    const navigate = useNavigate();
    const router = { push: navigate };
    const { setDatasetForm, setSuccessMessage, datasets, isLoading, isCreating, isModalOpen, datasetForm, errorMessage, successMessage, totalDatasets, totalSamples, usableDatasets, fetchDatasets, openCreateModal, closeCreateModal, handleCreateDataset, retryDataset, } = useDatasets();
    const { participants, createParticipant } = useParticipants();
    const { filteredJobs, selectedJob, setSearch: setAnnotationSearch, search: annotationSearch, setStatusFilter: setAnnotationStatusFilter, statusFilter: annotationStatusFilter, isLoading: isAnnotationPoolLoading, error: annotationPoolError, fetchJobs: fetchAnnotationJobs, selectJob, clearSelection, } = useAnnotationPool();
    const [activeTab, setActiveTab] = useState<"datasets" | "annotation-pool">("datasets");
    const reviewMetrics = (dataset: Dataset) => dataset as Dataset & DatasetReviewMetrics;
    const hasSamples = (dataset: Dataset) => dataset.sample_count > 0;
    const hasUnlabelledSamples = (dataset: Dataset) => dataset.sample_count > dataset.labelled_sample_count;
    const humanReviewedSummary = (dataset: Dataset) => {
        const metrics = reviewMetrics(dataset);
        const reviewed = metrics.human_reviewed_sample_count;
        const selected = metrics.review_selected_sample_count;
        if (typeof reviewed !== "number" || !Number.isFinite(reviewed)) {
            return "Not tracked";
        }
        return typeof selected === "number" && Number.isFinite(selected)
            ? `${reviewed}/${selected}`
            : String(reviewed);
    };
    const zipReviewStatus = (dataset: Dataset): string => {
        const metrics = reviewMetrics(dataset);
        const selected = metrics.review_selected_sample_count;
        const reviewed = metrics.human_reviewed_sample_count;
        const pending = metrics.pending_review_sample_count;
        if (typeof selected !== "number" || !Number.isFinite(selected)) {
            return "Review tracking unavailable";
        }
        if (selected === 0) {
            return "No samples selected";
        }
        if (typeof pending === "number" && pending > 0) {
            return `${pending} pending review`;
        }
        if (typeof reviewed === "number" &&
            Number.isFinite(reviewed) &&
            reviewed >= selected) {
            return "Review complete";
        }
        if (typeof reviewed === "number" && reviewed >= 0) {
            return "Review in progress";
        }
        return "Review status unavailable";
    };
    const isAnnotationReady = (dataset: Dataset) => dataset.status === "READY" && hasSamples(dataset);
    const isReviewComplete = (dataset: Dataset) => {
        if (!hasSamples(dataset))
            return false;
        if (isZipCollection(dataset)) {
            const metrics = reviewMetrics(dataset);
            const selected = metrics.review_selected_sample_count;
            const reviewed = metrics.human_reviewed_sample_count;
            return (typeof selected === "number" &&
                selected > 0 &&
                typeof reviewed === "number" &&
                reviewed >= selected);
        }
        return !hasUnlabelledSamples(dataset);
    };
    const openAnnotation = (datasetId: number) => {
        router.push(`/dataset/${datasetId}/annotate`);
    };
    const handleAddParticipant = async () => {
        const participant = await createParticipant();
        if (participant) {
            setDatasetForm(previous => ({ ...previous, participant: participant.id }));
            console.log(`Created participant ${participant.participant_code}`);
        }
    };
    const handleRetryDataset = async (datasetId: number) => {
        await retryDataset(datasetId);
    };
    const processingDatasetCount = (() => datasets.filter((dataset) => dataset.status === "PROCESSING").length)();
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const openImportModal = () => {
        setIsImportModalOpen(true);
    };
    const handleBulkImported = async (datasetName: string, videoCount: number) => {
        setSuccessMessage(`Imported ${videoCount} video(s) into "${datasetName}". ` +
            "Video processing has been queued.");
        await fetchDatasets(true);
    };
    function isZipCollection(dataset: Dataset): boolean {
        return !dataset.video_file && (dataset.video_count ?? 0) > 0;
    }
    function participantSummary(dataset: Dataset): string {
        if (isZipCollection(dataset)) {
            const count = dataset.participant_count;
            return count === null
                ? "Assigned per video"
                : `${count} participant${count === 1 ? "" : "s"}`;
        }
        return dataset.participant ? `p-${dataset.participant}` : "Unassigned";
    }
    function viewSummary(dataset: Dataset): string {
        if (isZipCollection(dataset)) {
            return dataset.view_angles?.length
                ? dataset.view_angles
                    .map((angle) => angle.charAt(0).toUpperCase() + angle.slice(1))
                    .join(",")
                : "Defined per video";
        }
        return dataset.view_angle == null
            ? ""
            : (VIEW_ANGLE_BY_ID[dataset.view_angle] ?? "Unknown");
    }
    function videoSummary(dataset: Dataset): string {
        if (!isZipCollection(dataset)) {
            return dataset.video_file ? "1 video" : "";
        }
        const total = dataset.video_count ?? 0;
        const ready = dataset.ready_video_count ?? 0;
        const failed = dataset.failed_video_count ?? 0;
        return `${ready}/${total} ready - ${failed} failed`;
    }
    function formatActivityDate(value: string): string {
        return new Date(value).toLocaleString();
    }
    function annotationStatusLabel(status: string): string {
        return status.replace("_", " ");
    }
    return (<><div {...scopeAttributes(input)} data-v-datasets="" className={cx("dataset-page")}><header data-v-datasets="" className={cx("page-header")}><div data-v-datasets="" className={cx("page-heading")}><div data-v-datasets="" className={cx("eyebrow")}><span data-v-datasets="" className={cx("eyebrow-dot")}></span>
    {" VECTOFIT DATA PIPELINE "}</div>
    <h1 data-v-datasets="">{"Datasets"}</h1>
    <p data-v-datasets="">{"Manage datasets used for VectoFit model training and evaluation."}</p></div>
    <div data-v-datasets="" className={cx("page-actions")}><button data-v-datasets="" type="button" onClick={() => openCreateModal()} className={cx("secondary-button")}>{" Add Single Video "}</button>
    <button data-v-datasets="" type="button" onClick={() => openImportModal()} className={cx("primary-button")}><span data-v-datasets="" className={cx("button-icon")}>{"↑"}</span>
    {" Import Dataset "}</button></div></header>
    <nav data-v-datasets="" aria-label="Dataset views" className={cx("page-tabs")}><button data-v-datasets="" type="button" aria-pressed={activeTab === 'datasets'} onClick={() => { setActiveTab('datasets'); }} className={cx("page-tab", { active: activeTab === 'datasets' })}>{" Datasets "}</button>
    <button data-v-datasets="" type="button" aria-pressed={activeTab === 'annotation-pool'} onClick={() => { setActiveTab('annotation-pool'); }} className={cx("page-tab", { active: activeTab === 'annotation-pool' })}>{" Annotation Pool "}</button></nav>
    {(successMessage) ? (<div data-v-datasets="" role="status" className={cx("feedback-message success")}>{display(successMessage)}</div>) : (null)}
    {(errorMessage) ? (<div data-v-datasets="" role="alert" className={cx("feedback-message error")}>{display(errorMessage)}</div>) : (null)}
        {(activeTab === 'datasets') ? (<section data-v-datasets="" className={cx("summary-grid")}><SummaryCard data-v-datasets="" label="Datasets" value={totalDatasets} description="Registered datasets" icon="D" variant="samples"></SummaryCard>
        <SummaryCard data-v-datasets="" label="Samples" value={totalSamples} description="Completed squat repetitions" icon="Σ" variant="samples"></SummaryCard>
        <SummaryCard data-v-datasets="" label="Training Ready" value={usableDatasets.length} description="Datasets with labelled samples" icon="✓" variant="correct"></SummaryCard>
        <SummaryCard data-v-datasets="" label="Processing" value={processingDatasetCount} description="Currently being processed" icon="↻" variant="version"></SummaryCard></section>) : (null)}
        {(activeTab === 'datasets') ? (<section data-v-datasets="" className={cx("content-card")}><div data-v-datasets="" className={cx("section-header")}><div data-v-datasets="" className={cx("section-title-row")}><div data-v-datasets="" className={cx("section-marker")}></div>
        <div data-v-datasets=""><h2 data-v-datasets="">{"Datasets"}</h2>
        <p data-v-datasets="">{"Registered exercise data and preprocessing status."}</p></div></div></div>
            {(!isLoading && datasets.length === 0) ? (<DatasetEmptyState data-v-datasets="" onAction={openCreateModal}></DatasetEmptyState>) : ((isLoading) ? (<div data-v-datasets="" aria-live="polite" className={cx("loading-state")}><span data-v-datasets="" aria-hidden="true" className={cx("loading-dot")}></span>
            {" Loading datasets... "}</div>) : (<div data-v-datasets="" className={cx("dataset-table-wrapper")}><table data-v-datasets="" className={cx("dataset-table")}><thead data-v-datasets=""><tr data-v-datasets=""><th data-v-datasets="">{"Dataset"}</th>
            <th data-v-datasets="">{"Type"}</th>
            <th data-v-datasets="">{"Participants"}</th>
            <th data-v-datasets="">{"View Angles"}</th>
            <th data-v-datasets="">{"Exercise"}</th>
            <th data-v-datasets="">{"Purpose"}</th>
            <th data-v-datasets="">{"Videos"}</th>
            <th data-v-datasets="">{"Samples"}</th>
            <th data-v-datasets=""><span data-v-datasets="" title="A sample may have inherited its label from a ZIP folder; this does not prove human review.">{" Labelled "}</span></th>
            <th data-v-datasets="">{"Human reviewed"}</th>
            <th data-v-datasets="">{"Status"}</th>
            <th data-v-datasets="">{"Actions"}</th></tr></thead>
            <tbody data-v-datasets="">{each(datasets).map(([_index, dataset]) => (<tr data-v-datasets="" key={dataset.id}><td data-v-datasets=""><div data-v-datasets="" className={cx("dataset-name")}><strong data-v-datasets="">{display(dataset.name)}</strong>
                <span data-v-datasets="" className={cx("dataset-id")}>{"#"}
                {display(dataset.id)}</span></div></td>
                <td data-v-datasets=""><span data-v-datasets="" title={isZipCollection(dataset)
                        ? 'A collection of individual video records'
                        : 'A dataset containing one video'} className={cx("exercise-value")}>{display(isZipCollection(dataset) ? "ZIP" : "Single video")}</span></td>
                <td data-v-datasets="">{(!isZipCollection(dataset) && dataset.participant) ? (<span data-v-datasets="" className={cx("participant-value")}>{" P-"}
                    {display(dataset.participant)}</span>) : (<span data-v-datasets="" className={cx("muted-value")}>{display(participantSummary(dataset))}</span>)}</td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("muted-value")}>{display(viewSummary(dataset))}</span></td>
                <td data-v-datasets="">{display(dataset.exercise_type)}</td>
                <td data-v-datasets="">{display(dataset.purpose)}</td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("sample-count")}>{display(videoSummary(dataset))}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("sample-count")}>{display(dataset.sample_count)}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" title={`${dataset.labelled_sample_count} of ${dataset.sample_count} repetitions have a binary label; labels may be inherited from ZIP folders.`} className={cx("labelled-count")}><strong data-v-datasets="">{display(dataset.labelled_sample_count)}</strong>
                {" / "}
                {display(dataset.sample_count)}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("labelled-count")}>{display(humanReviewedSummary(dataset))}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("status-badge", `status-${dataset.status.toLowerCase()}`)}>{(dataset.status === 'PROCESSING') ? (<span data-v-datasets=""></span>) : (null)}
                {" "}
                {display(dataset.status)}</span></td>
                <td data-v-datasets=""><div data-v-datasets="" className={cx("action-cell")}>{(isAnnotationReady(dataset)) ? (<button data-v-datasets="" type="button" onClick={() => { openAnnotation(dataset.id); }} className={cx("action-button")}>{" Annotate "}</button>) : ((dataset.status === 'READY' && isReviewComplete(dataset)) ? (<span data-v-datasets="" className={cx("action-complete")}>{display(isZipCollection(dataset) ? "Review complete" : "Complete")}</span>) : ((dataset.status === 'READY' && isZipCollection(dataset)) ? (<span data-v-datasets="" title="ZIP folder labels are source labels. Manual-review completion is tracked separately." className={cx("muted-value")}>{display(zipReviewStatus(dataset))}</span>) : ((dataset.status === 'PROCESSING') ? (<span data-v-datasets="" className={cx("processing-state")}><span data-v-datasets="" className={cx("processing-spinner")}></span></span>) : ((isZipCollection(dataset) &&
                        ['PARTIAL', 'FAILED'].includes(dataset.status)) ? (<span data-v-datasets="" title={`${dataset.failed_video_count ?? 0} video(s) failed processing`} className={cx("muted-value")}>{" Check videos "}</span>) : ((dataset.status === 'FAILED' && !isZipCollection(dataset)) ? (<button data-v-datasets="" type="button" onClick={() => { handleRetryDataset(dataset.id); }} className={cx("action-button retry-button")}>{" Retry "}</button>) : ((dataset.status === 'PENDING') ? (<span data-v-datasets="" className={cx("muted-value")}>{" Queued "}</span>) : (<span data-v-datasets="" className={cx("muted-value")}></span>)))))))}</div></td></tr>))}</tbody></table></div>))}</section>) : (null)}
        {(activeTab === 'datasets') ? (<section data-v-datasets="" className={cx("content-card")}><div data-v-datasets="" className={cx("section-header")}><div data-v-datasets="" className={cx("section-title-row")}><div data-v-datasets="" className={cx("section-marker")}></div>
        <div data-v-datasets=""><h2 data-v-datasets="">{"Dataset Structure"}</h2>
        <p data-v-datasets="">{"Each completed squat repetition represents one sample."}</p></div></div></div>
        <StructureGrid data-v-datasets=""></StructureGrid></section>) : (<section data-v-datasets="" className={cx("content-card annotation-pool-card")}><div data-v-datasets="" className={cx("section-header")}><div data-v-datasets="" className={cx("section-title-row")}><div data-v-datasets="" className={cx("section-marker")}></div>
        <div data-v-datasets=""><h2 data-v-datasets="">{"Annotation Pool"}</h2>
        <p data-v-datasets="">{"Dataset-level annotation jobs and their complete activity log."}</p></div></div>
        <button data-v-datasets="" type="button" disabled={isAnnotationPoolLoading} onClick={() => fetchAnnotationJobs()} className={cx("secondary-button")}>{" Refresh "}</button></div>
        <div data-v-datasets="" className={cx("annotation-pool-toolbar")}><input data-v-datasets="" value={annotationSearch ?? ''} onChange={(event) => setAnnotationSearch(event.target.value)} type="search" placeholder="Search dataset or annotator" aria-label="Search annotation jobs" className={cx("pool-search")}/>
        <select data-v-datasets="" value={annotationStatusFilter ?? ''} onChange={(event) => setAnnotationStatusFilter(event.target.value)} aria-label="Filter annotation jobs by status" className={cx("pool-filter")}><option data-v-datasets="" value="ALL">{"All statuses"}</option>
        <option data-v-datasets="" value="QUEUED">{"Queued"}</option>
        <option data-v-datasets="" value="IN_PROGRESS">{"In progress"}</option>
        <option data-v-datasets="" value="COMPLETED">{"Completed"}</option>
        <option data-v-datasets="" value="NO_SAMPLES">{"No samples"}</option></select></div>
            {(annotationPoolError) ? (<div data-v-datasets="" className={cx("pool-message error")}>{display(annotationPoolError)}</div>) : ((isAnnotationPoolLoading) ? (<div data-v-datasets="" className={cx("loading-state")}><span data-v-datasets="" aria-hidden="true" className={cx("loading-dot")}></span>
            {" Loading annotation activity... "}</div>) : ((filteredJobs.length === 0) ? (<div data-v-datasets="" className={cx("empty-state")}>{" No annotation jobs match the current filters. "}</div>) : (<div data-v-datasets="" className={cx("annotation-pool-layout")}><div data-v-datasets="" className={cx("pool-table-wrapper")}><table data-v-datasets="" className={cx("dataset-table pool-table")}><thead data-v-datasets=""><tr data-v-datasets=""><th data-v-datasets="">{"Dataset"}</th>
            <th data-v-datasets="">{"Status"}</th>
            <th data-v-datasets="">{"Progress"}</th>
            <th data-v-datasets="">{"Activity"}</th>
            <th data-v-datasets="">{"Annotators"}</th>
            <th data-v-datasets="">{"Updated"}</th></tr></thead>
            <tbody data-v-datasets="">{each(filteredJobs).map(([_index, job]) => (<tr data-v-datasets="" key={job.id} tabIndex={0} onClick={() => { selectJob(job); }} onKeyDown={() => { selectJob(job); }} className={cx("pool-row", { selected: selectedJob?.id === job.id })}><td data-v-datasets=""><div data-v-datasets="" className={cx("dataset-name")}><strong data-v-datasets="">{display(job.name)}</strong>
                <span data-v-datasets="" className={cx("dataset-id")}>{"Job #"}
                {display(job.id)}</span></div></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("pool-status", `pool-status-${job.job_status.toLowerCase()}`)}>{display(annotationStatusLabel(job.job_status))}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("sample-count")}>{display(job.reviewed_count)}
                {" / "}
                {display(job.sample_count)}</span>
                <span data-v-datasets="" className={cx("pool-subtext")}>{"samples reviewed"}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("sample-count")}>{display(job.activity_count)}</span>
                <span data-v-datasets="" className={cx("pool-subtext")}>{"logged actions"}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("pool-subtext")}>{display(job.annotators.length
                        ? job.annotators
                            .map((item) => item.annotator?.username ?? "Unassigned")
                            .join(", ")
                        : "No activity")}</span></td>
                <td data-v-datasets=""><span data-v-datasets="" className={cx("pool-subtext")}>{display(formatActivityDate(job.last_activity_at))}</span></td></tr>))}</tbody></table></div>
                {(selectedJob) ? (<aside data-v-datasets="" className={cx("pool-details")}><div data-v-datasets="" className={cx("pool-details-header")}><div data-v-datasets=""><span data-v-datasets="" className={cx("dataset-id")}>{"DATASET #"}
                {display(selectedJob.id)}</span>
                <h3 data-v-datasets="">{display(selectedJob.name)}</h3></div>
                <button data-v-datasets="" type="button" aria-label="Close annotation details" onClick={() => clearSelection()} className={cx("close-details")}>{" × "}</button></div>
                <div data-v-datasets="" className={cx("pool-metrics")}><div data-v-datasets=""><strong data-v-datasets="">{display(selectedJob.sample_count)}</strong>
                <span data-v-datasets="">{"Samples"}</span></div>
                <div data-v-datasets=""><strong data-v-datasets="">{display(selectedJob.reviewed_count)}</strong>
                <span data-v-datasets="">{"Reviewed"}</span></div>
                <div data-v-datasets=""><strong data-v-datasets="">{display(selectedJob.pending_count)}</strong>
                <span data-v-datasets="">{"Pending"}</span></div></div>
                <h4 data-v-datasets="">{"Activity log"}</h4>
                    {(selectedJob.activity.length === 0) ? (<div data-v-datasets="" className={cx("pool-subtext")}>{" No annotation activity has been logged yet. "}</div>) : (<ul data-v-datasets="" className={cx("activity-list")}>{each(selectedJob.activity).map(([_index, activity]) => (<li data-v-datasets="" key={activity.id}><div data-v-datasets=""><strong data-v-datasets="">{"Sample #"}
                        {display(activity.sample_id)}</strong>
                        <span data-v-datasets="">{display(activity.annotator?.username ?? "Unassigned")}</span>
                            {(activity.annotation) ? (<span data-v-datasets="">{" Left: "}
                            {display(activity.annotation.left.grade)}
                            {" ("}
                            {display(activity.annotation.left.direction)}
                            {") / Right: "}
                            {display(activity.annotation.right.grade)}
                            {" ("}
                            {display(activity.annotation.right.direction)}
                            {") "}</span>) : (null)}
                            {(activity.annotation) ? (<span data-v-datasets="">{"Symmetry: "}
                            {display(activity.annotation.symmetry_observation)}
                            {" / "}
                            {display(activity.annotation.notes)}</span>) : (<span data-v-datasets="">{"Rating cleared"}</span>)}
                        <span data-v-datasets="">{display(activity.rubric_version)}</span></div>
                        <time data-v-datasets="" dateTime={activity.created_at}>{display(formatActivityDate(activity.created_at))}</time></li>))}</ul>)}</aside>) : (null)}</div>)))}</section>)}
    <CreateDatasetModal onFormChange={setDatasetForm} data-v-datasets="" isOpen={isModalOpen} isSubmitting={isCreating} form={datasetForm} participants={participants} onCreateParticipant={handleAddParticipant} onClose={closeCreateModal} onSubmit={handleCreateDataset}></CreateDatasetModal>
    <DatasetImportModal data-v-datasets="" isOpen={isImportModalOpen} onClose={() => { setIsImportModalOpen(false); }} onImported={handleBulkImported}></DatasetImportModal></div></>);
}
