import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useEffect } from 'react';
import type { ChangeEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../query';
import { useDialogFocus } from "../../composables/useDialogFocus";
import { datasetService, type DatasetImportPreview, type DatasetImportFile, } from "../../services/datasetService";
import { bindStyles, each, display } from '../../presentation';
import styles from './DatasetImportModal.module.css';
type ReviewPolicy = "source" | "all" | "subset";
type SelectionMethod = "stratified" | "manual";
type Callbacks = {
    onClose?: () => void;
    onImported?: (datasetName: string, videoCount: number) => void;
};
export default function DatasetImportModal(input: {
    isOpen: boolean;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { isOpen } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "close"): void;
        (event: "imported", datasetName: string, videoCount: number): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "close":
            props.onClose?.(...args as [
            ]);
            break;
        case "imported":
            props.onImported?.(...args as [
                datasetName: string,
                videoCount: number
            ]);
            break;
    } }) as Emit;
    const cache = useQueryClient();
    const previewRequest = useMutation({ mutationFn: datasetService.previewDatasetArchive });
    const importRequest = useMutation({ mutationFn: datasetService.commitDatasetArchive, onSuccess: () => cache.invalidateQueries({ queryKey: queryKeys.datasets }) });
    const dialogRef = useRef<HTMLElement | null>(null);
    useDialogFocus(() => props.isOpen, dialogRef);
    const DEFAULT_NAME = "VectoFit Bodyweight Squat v1";
    const DEFAULT_DESCRIPTION = "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.";
    const zipInput = useRef<HTMLInputElement | null>(null);
    const [zipFile, setZipFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<DatasetImportPreview | null>(null);
    const [name, setName] = useState(DEFAULT_NAME);
    const [description, setDescription] = useState(DEFAULT_DESCRIPTION);
    const [exerciseType, setExerciseType] = useState("bodyweight_squat");
    const [purpose, setPurpose] = useState("training");
    const [primaryTarget, setPrimaryTarget] = useState("squat_quality");
    const [secondaryTarget, setSecondaryTarget] = useState("biomechanical_errors");
    const [reviewPolicy, setReviewPolicy] = useState<ReviewPolicy>("subset");
    const [selectionMethod, setSelectionMethod] = useState<SelectionMethod>("stratified");
    const [reviewCount, setReviewCount] = useState(10);
    const [randomSeed, setRandomSeed] = useState(42);
    const [selectedVideoPaths, setSelectedVideoPaths] = useState<string[]>([]);
    const [isPreviewing, setIsPreviewing] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [importCompleted, setImportCompleted] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [outcomeMessage, setOutcomeMessage] = useState("");
    const isBusy = (() => isPreviewing || isImporting)();
    const manifestFiles = (() => preview?.manifest.files ?? [])();
    const reviewableFiles = (() => manifestFiles.filter((file) => Boolean(file.archive_path)))();
    const effectiveReviewCount = (() => {
        if (reviewPolicy === "source")
            return 0;
        if (reviewPolicy === "all")
            return reviewableFiles.length;
        return selectedVideoPaths.length;
    })();
    const untouchedCount = (() => reviewableFiles.length - effectiveReviewCount)();
    const canGenerateSelection = (() => reviewPolicy === "subset" &&
        selectionMethod === "stratified" &&
        reviewableFiles.length > 0)();
    const canImportReason = (() => {
        if (isBusy)
            return "Import is in progress.";
        if (importCompleted)
            return "This archive has already been imported.";
        if (!zipFile)
            return "Choose a ZIP archive to begin.";
        if (!name.trim())
            return "Enter a dataset name.";
        if (!preview?.upload_token) {
            return "Preview the archive before importing.";
        }
        if (preview.manifest.errors.length > 0) {
            return "The archive has validation errors.";
        }
        if (reviewPolicy === "subset" && effectiveReviewCount === 0) {
            return "Select at least one video for manual review.";
        }
        return "";
    })();
    const canImport = (() => !canImportReason)();
    function reset() {
        setZipFile(null);
        setPreview(null);
        setErrorMessage("");
        setOutcomeMessage("");
        setIsPreviewing(false);
        setIsImporting(false);
        setImportCompleted(false);
        setReviewPolicy("subset");
        setSelectionMethod("stratified");
        setReviewCount(10);
        setRandomSeed(42);
        setSelectedVideoPaths([]);
        setName(DEFAULT_NAME);
        setDescription(DEFAULT_DESCRIPTION);
        setExerciseType("bodyweight_squat");
        setPurpose("training");
        setPrimaryTarget("squat_quality");
        setSecondaryTarget("biomechanical_errors");
        if (zipInput.current)
            zipInput.current.value = "";
    }
    useEffect(() => {
        if (!props.isOpen && !isBusy)
            reset();
    }, [props.isOpen]);
    function close() {
        if (isBusy)
            return;
        emit("close");
    }
    function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0] ?? null;
        setPreview(null);
        setSelectedVideoPaths([]);
        setErrorMessage("");
        setOutcomeMessage("");
        setImportCompleted(false);
        if (!file) {
            setZipFile(null);
            return;
        }
        if (!file.name.toLowerCase().endsWith(".zip")) {
            setZipFile(null);
            input.value = "";
            setErrorMessage("Please select a ZIP archive.");
            return;
        }
        setZipFile(file);
    }
    function getErrorMessage(error: unknown): string | null {
        if (!error || typeof error !== "object") {
            return error instanceof Error ? error.message : null;
        }
        const candidate = error as {
            message?: unknown;
            response?: {
                data?: Record<string, unknown>;
            };
        };
        const data = candidate.response?.data;
        for (const value of [
            data?.detail,
            data?.message,
            data?.error,
            ...Object.values(data ?? {}),
        ]) {
            if (typeof value === "string" && value.trim()) {
                return value;
            }
            if (Array.isArray(value)) {
                const message = value.find((item): item is string => typeof item === "string" && item.trim().length > 0);
                if (message)
                    return message;
            }
        }
        return typeof candidate.message === "string" ? candidate.message : null;
    }
    function hashString(value: string): number {
        let hash = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
            hash ^= value.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
        }
        return hash >>> 0;
    }
    function generateStratifiedSelection(files: DatasetImportFile[] = reviewableFiles): string[] {
        if (!files.length)
            return [];
        const count = Math.max(1, Math.min(files.length, Math.floor(reviewCount)));
        const groups = new Map<string, typeof files>();
        for (const file of files) {
            const label = file.source_label ? "good" : "bad";
            const angle = file.view_angle || "unknown";
            const key = `${label}:${angle}`;
            if (!groups.has(key))
                groups.set(key, []);
            groups.get(key)!.push(file);
        }
        const seed = String(randomSeed);
        for (const [key, group] of groups) {
            group.sort((a, b) => hashString(`${seed}:${key}:${a.archive_path}`) -
                hashString(`${seed}:${key}:${b.archive_path}`));
        }
        const orderedGroups = [...groups.entries()]
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([, group]) => group);
        const selected: string[] = [];
        let cursor = 0;
        while (selected.length < count &&
            orderedGroups.some((group) => group.length > 0)) {
            const group = orderedGroups[cursor % orderedGroups.length];
            if (group.length > 0) {
                selected.push(group.shift()!.archive_path);
            }
            cursor += 1;
        }
        return selected;
    }
    function generateSelection() {
        if (selectionMethod !== "stratified")
            return;
        setSelectedVideoPaths(generateStratifiedSelection());
    }
    function toggleVideo(path: string, checked: boolean) {
        if (checked) {
            if (!selectedVideoPaths.includes(path)) {
                setSelectedVideoPaths([...selectedVideoPaths, path]);
            }
        }
        else {
            setSelectedVideoPaths(selectedVideoPaths.filter((item) => item !== path));
        }
    }
    function toggleAllVideos() {
        const allPaths = reviewableFiles.map((file) => file.archive_path);
        setSelectedVideoPaths(selectedVideoPaths.length === allPaths.length ? [] : allPaths);
    }
    useEffect(() => {
        const policy = reviewPolicy;
        const method = selectionMethod;
        if (policy === "all") {
            setSelectedVideoPaths(reviewableFiles.map((file) => file.archive_path));
        }
        else if (policy === "source") {
            setSelectedVideoPaths([]);
        }
        else if (method === "stratified" && preview) {
            generateSelection();
        }
    }, [reviewPolicy, selectionMethod]);
    async function previewArchive() {
        if (isBusy)
            return;
        if (!zipFile) {
            setErrorMessage("Select a ZIP archive first.");
            return;
        }
        setIsPreviewing(true);
        setPreview(null);
        setSelectedVideoPaths([]);
        setErrorMessage("");
        setOutcomeMessage("");
        try {
            const result = await previewRequest.mutateAsync(zipFile);
            setPreview(result);
            if (result.manifest.errors.length > 0) {
                setErrorMessage("The archive has validation errors. Correct the archive and upload it again.");
            }
            else if (!result.upload_token) {
                setErrorMessage("The preview did not return an upload token. Please preview again.");
            }
            else if (reviewPolicy === "subset") {
                setSelectedVideoPaths(generateStratifiedSelection(result.manifest.files.filter(file => Boolean(file.archive_path))));
            }
            else if (reviewPolicy === "all") {
                setSelectedVideoPaths(result.manifest.files.filter(file => Boolean(file.archive_path)).map(file => file.archive_path));
            }
        }
        catch (error: unknown) {
            setErrorMessage(getErrorMessage(error) ?? "Could not preview the archive.");
        }
        finally {
            setIsPreviewing(false);
        }
    }
    async function commitImport() {
        const currentPreview = preview;
        if (!currentPreview?.upload_token || !canImport) {
            return;
        }
        if (isBusy || importCompleted)
            return;
        if (!canImport) {
            setErrorMessage(canImportReason);
            return;
        }
        setIsImporting(true);
        setErrorMessage("");
        setOutcomeMessage("");
        try {
            const result = await importRequest.mutateAsync({
                upload_token: currentPreview.upload_token,
                name: name.trim(),
                description: description.trim(),
                exercise_type: exerciseType,
                purpose: purpose,
                primary_target: primaryTarget.trim(),
                secondary_target: secondaryTarget.trim(),
                review_policy: reviewPolicy,
                selection_method: selectionMethod,
                review_count: reviewPolicy === "subset"
                    ? effectiveReviewCount
                    : undefined,
                random_seed: reviewPolicy === "subset" &&
                    selectionMethod === "stratified"
                    ? randomSeed
                    : undefined,
                selected_video_paths: reviewPolicy === "subset" ? [...selectedVideoPaths] : [],
            });
            setImportCompleted(true);
            emit("imported", result.dataset.name, result.imported_videos);
            if (result.queue_failures.length > 0) {
                setOutcomeMessage(`Dataset "${result.dataset.name}" was imported, but ` +
                    `${result.queue_failures.length} video(s) could not be queued. ` +
                    `Imported: ${result.imported_videos}. ` +
                    `Queued: ${result.queued_videos}. ` +
                    "Check video processing statuses before training.");
                return;
            }
            emit("close");
        }
        catch (error: unknown) {
            setErrorMessage(getErrorMessage(error) ?? "Dataset import failed.");
        }
        finally {
            setIsImporting(false);
        }
    }
    return (<>{createPortal(<>{(isOpen) ? (<div data-v-dataset-import-modal="" onClick={(event) => { if (event.target !== event.currentTarget)
                return; close(); }} onKeyDown={(event) => { if (event.key !== 'Escape')
                return; close(); }} className={cx("import-overlay")}><section data-v-dataset-import-modal="" ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="import-title" className={cx("import-modal")}><header data-v-dataset-import-modal="" className={cx("import-header")}><div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="" className={cx("eyebrow")}>{"VECTOFIT DATA PIPELINE"}</span>
            <h2 data-v-dataset-import-modal="" id="import-title">{"Import Dataset"}</h2>
            <p data-v-dataset-import-modal="">{" Upload a ZIP archive, review its manifest, and configure annotation. "}</p></div>
            <button data-v-dataset-import-modal="" type="button" aria-label="Close import dialog" disabled={isBusy} onClick={() => close()} className={cx("close-button")}>{" ✕ "}</button></header>
            <div data-v-dataset-import-modal="" className={cx("import-body")}><section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"1. Dataset information"}</h3>
            <div data-v-dataset-import-modal="" className={cx("form-grid")}><label data-v-dataset-import-modal="">{" Dataset name "}
            <input data-v-dataset-import-modal="" value={name ?? ''} onChange={(event) => setName(event.target.value)} maxLength={50} required autoComplete="off" placeholder="Enter dataset name"/></label>
            <label data-v-dataset-import-modal="">{" Exercise "}
            <select data-v-dataset-import-modal="" value={exerciseType ?? ''} onChange={(event) => setExerciseType(event.target.value)}><option data-v-dataset-import-modal="" value="bodyweight_squat">{"Bodyweight Squat"}</option>
            <option data-v-dataset-import-modal="" value="goblet_squat">{"Goblet Squat"}</option></select></label>
            <label data-v-dataset-import-modal="" className={cx("full-width")}>{" Description "}
            <textarea data-v-dataset-import-modal="" value={description ?? ''} onChange={(event) => setDescription(event.target.value)} rows={2} placeholder="Describe the dataset"></textarea></label></div></section>
            <section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"2. Upload ZIP archive"}</h3>
            <p data-v-dataset-import-modal="" className={cx("section-hint")}>{" Supported formats: MP4, MOV, M4V, and AVI. Class labels and camera angles must be recognizable from archive folders or filenames. "}</p>
            <label data-v-dataset-import-modal="" htmlFor="dataset-archive" className={cx("file-picker")}><span data-v-dataset-import-modal="" aria-hidden="true" className={cx("file-picker-icon")}>{"↑"}</span>
            <strong data-v-dataset-import-modal="">{display(zipFile?.name || "Choose dataset ZIP")}</strong>
            <small data-v-dataset-import-modal="">{display(zipFile
                    ? `${(zipFile.size / 1024 / 1024).toFixed(1)} MB`
                    : "Select a ZIP archive containing your videos")}</small>
            <input data-v-dataset-import-modal="" id="dataset-archive" ref={zipInput} type="file" accept=".zip,application/zip" disabled={isBusy || importCompleted} onChange={handleFileChange}/></label>
            <p data-v-dataset-import-modal="" className={cx("section-hint")}>{" ZIP labels are source-provided labels. They do not mean a human has reviewed the repetitions. "}</p>
            <button data-v-dataset-import-modal="" type="button" disabled={!zipFile || isBusy || importCompleted} onClick={() => previewArchive()} className={cx("secondary-button preview-button")}>{display(isPreviewing ? "Inspecting archive..." : "Preview archive")}</button></section>
                {(preview) ? (<><section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"3. Review manifest"}</h3>
                <div data-v-dataset-import-modal="" className={cx("manifest-summary")}><div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Recognized videos"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.file_count)}</strong></div>
                <div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Participants"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.participant_count)}</strong></div>
                <div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Good videos"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.by_label.good)}</strong></div>
                <div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Bad videos"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.by_label.bad)}</strong></div></div>
                <div data-v-dataset-import-modal="" className={cx("angle-summary")}><span data-v-dataset-import-modal="">{"Diagonal: "}
                {display(preview.manifest.by_angle.diagonal)}</span>
                <span data-v-dataset-import-modal="">{"Frontal: "}
                {display(preview.manifest.by_angle.frontal)}</span>
                <span data-v-dataset-import-modal="">{"Sagittal: "}
                {display(preview.manifest.by_angle.sagittal)}</span></div>
                    {(preview.manifest.errors.length) ? (<div data-v-dataset-import-modal="" role="alert" className={cx("message error")}><strong data-v-dataset-import-modal="">{"Cannot import yet"}</strong>
                    <ul data-v-dataset-import-modal="">{each(preview.manifest.errors).map(([_index, item]) => (<li data-v-dataset-import-modal="" key={item}>{display(item)}</li>))}</ul></div>) : (null)}
                    {(preview.manifest.warnings.length) ? (<div data-v-dataset-import-modal="" role="status" className={cx("message warning")}><strong data-v-dataset-import-modal="">{"Review these warnings"}</strong>
                    <ul data-v-dataset-import-modal="">{each(preview.manifest.warnings).map(([_index, item]) => (<li data-v-dataset-import-modal="" key={item}>{display(item)}</li>))}</ul></div>) : (null)}</section>
                <section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"4. Labeling & review policy"}</h3>
                <label data-v-dataset-import-modal="" className={cx("policy-option")}><input data-v-dataset-import-modal="" checked={reviewPolicy === "source"} onChange={() => setReviewPolicy("source")} type="radio" value="source"/>
                <span data-v-dataset-import-modal=""><strong data-v-dataset-import-modal="">{"Use ZIP labels only"}</strong>
                <small data-v-dataset-import-modal="">{"Inherit source labels; do not select videos for manual review."}</small></span></label>
                <label data-v-dataset-import-modal="" className={cx("policy-option")}><input data-v-dataset-import-modal="" checked={reviewPolicy === "all"} onChange={() => setReviewPolicy("all")} type="radio" value="all"/>
                <span data-v-dataset-import-modal=""><strong data-v-dataset-import-modal="">{"Review every video"}</strong>
                <small data-v-dataset-import-modal="">{"Select all imported videos for manual annotation."}</small></span></label>
                <label data-v-dataset-import-modal="" className={cx("policy-option")}><input data-v-dataset-import-modal="" checked={reviewPolicy === "subset"} onChange={() => setReviewPolicy("subset")} type="radio" value="subset"/>
                <span data-v-dataset-import-modal=""><strong data-v-dataset-import-modal="">{"Review a selected subset"}</strong>
                <small data-v-dataset-import-modal="">{"Select individual videos or sample across labels and views."}</small></span></label>
                    {(reviewPolicy === 'subset') ? (<div data-v-dataset-import-modal="" className={cx("selection-settings")}><label data-v-dataset-import-modal="">{" Selection method "}
                    <select data-v-dataset-import-modal="" value={selectionMethod ?? ''} onChange={(event) => setSelectionMethod(event.target.value as SelectionMethod)}><option data-v-dataset-import-modal="" value="stratified">{"Stratified random"}</option>
                    <option data-v-dataset-import-modal="" value="manual">{"Manual selection"}</option></select></label>
                        {(selectionMethod === 'stratified') ? (<><label data-v-dataset-import-modal="">{" Videos to review "}
                        <input data-v-dataset-import-modal="" value={reviewCount ?? ''} onChange={(event) => setReviewCount(Number(event.target.value))} type="number" min="1" max={reviewableFiles.length || 1}/></label>
                        <label data-v-dataset-import-modal="">{" Random seed "}
                        <input data-v-dataset-import-modal="" value={randomSeed ?? ''} onChange={(event) => setRandomSeed(Number(event.target.value))} type="number"/></label>
                        <button data-v-dataset-import-modal="" type="button" disabled={!canGenerateSelection || isBusy} onClick={() => generateSelection()} className={cx("secondary-button")}>{" Generate selection "}</button></>) : (<button data-v-dataset-import-modal="" type="button" onClick={() => toggleAllVideos()} className={cx("secondary-button")}>{display(selectedVideoPaths.length === reviewableFiles.length
                                ? "Clear selection"
                                : "Select all videos")}</button>)}</div>) : (null)}
                <div data-v-dataset-import-modal="" className={cx("review-summary")}><div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Selected for review"}</span>
                <strong data-v-dataset-import-modal="">{display(effectiveReviewCount)}</strong></div>
                <div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Left untouched"}</span>
                <strong data-v-dataset-import-modal="">{display(untouchedCount)}</strong></div></div>
                <p data-v-dataset-import-modal="" className={cx("section-hint")}>{" Selection is based on whole videos, not individual repetitions. Source labels remain distinct from human annotation status. "}</p>
                <div data-v-dataset-import-modal="" className={cx("manifest-table-wrapper")}><table data-v-dataset-import-modal="" className={cx("manifest-table")}><thead data-v-dataset-import-modal=""><tr data-v-dataset-import-modal="">{(reviewPolicy === 'subset' &&
                        selectionMethod === 'manual') ? (<th data-v-dataset-import-modal="">{" Review "}</th>) : (null)}
                <th data-v-dataset-import-modal="">{"Participant"}</th>
                <th data-v-dataset-import-modal="">{"View"}</th>
                <th data-v-dataset-import-modal="">{"ZIP label"}</th>
                <th data-v-dataset-import-modal="">{"Review state"}</th>
                <th data-v-dataset-import-modal="">{"Archive path"}</th></tr></thead>
                <tbody data-v-dataset-import-modal="">{each(preview.manifest.files).map(([_index, file]) => (<tr data-v-dataset-import-modal="" key={file.archive_path}>{(reviewPolicy === 'subset' &&
                            selectionMethod === 'manual') ? (<td data-v-dataset-import-modal=""><input data-v-dataset-import-modal="" type="checkbox" checked={selectedVideoPaths.includes(file.archive_path)} aria-label={`Review ${file.archive_path}`} onChange={(event) => {
                                toggleVideo(file.archive_path, (event.target as HTMLInputElement).checked);
                            }}/></td>) : (null)}
                    <td data-v-dataset-import-modal="">{display(file.participant_code)}</td>
                    <td data-v-dataset-import-modal="">{display(file.view_angle)}</td>
                    <td data-v-dataset-import-modal=""><span data-v-dataset-import-modal="" className={cx([
                            'label-chip',
                            file.source_label ? 'good' : 'bad',
                        ])}>{display(file.source_label ? "Good" : "Bad")}</span></td>
                    <td data-v-dataset-import-modal="">{display(reviewPolicy === "all" ||
                            (reviewPolicy === "subset" &&
                                selectedVideoPaths.includes(file.archive_path))
                            ? "Selected for review"
                            : "Untouched")}</td>
                    <td data-v-dataset-import-modal="" className={cx("path-cell")}>{display(file.archive_path)}</td></tr>))}</tbody></table></div></section></>) : (null)}
            {(errorMessage) ? (<div data-v-dataset-import-modal="" role="alert" className={cx("message error")}>{display(errorMessage)}</div>) : (null)}
            {(outcomeMessage) ? (<div data-v-dataset-import-modal="" role="status" className={cx("message warning")}>{display(outcomeMessage)}</div>) : (null)}</div>
            <footer data-v-dataset-import-modal="" className={cx("import-footer")}>{(!canImport && !importCompleted) ? (<p data-v-dataset-import-modal="" role="status" className={cx("import-blocker")}>{display(canImportReason)}</p>) : ((importCompleted) ? (<p data-v-dataset-import-modal="" role="status" className={cx("import-blocker")}>{" This archive has already been submitted successfully. "}</p>) : (null))}
            <div data-v-dataset-import-modal="" className={cx("import-actions")}><button data-v-dataset-import-modal="" type="button" disabled={isBusy} onClick={() => close()} className={cx("secondary-button")}>{display(importCompleted ? "Close" : "Cancel")}</button>
            <button data-v-dataset-import-modal="" type="button" disabled={!canImport} onClick={() => commitImport()} className={cx("primary-button")}>{(isImporting) ? (<span data-v-dataset-import-modal="" aria-hidden="true" className={cx("spinner")}></span>) : (null)}
            {" "}
                {display(isImporting
                    ? "Importing and queueing..."
                    : importCompleted
                        ? "Import completed"
                        : "Import")}</button></div></footer></section></div>) : (null)}</>, document.body)}</>);
}
