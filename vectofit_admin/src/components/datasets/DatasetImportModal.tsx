import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useEffect } from 'react';
import type { ChangeEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../query';
import { useDialogFocus } from "../../composables/useDialogFocus";
import { datasetService, type DatasetImportPreview, } from "../../services/datasetService";
import { bindStyles, each, display } from '../../presentation';
import styles from './DatasetImportModal.module.css';
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
    const DEFAULT_DESCRIPTION = "Bodyweight squat recordings for human knee annotation.";
    const zipInput = useRef<HTMLInputElement | null>(null);
    const [zipFile, setZipFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<DatasetImportPreview | null>(null);
    const [name, setName] = useState(DEFAULT_NAME);
    const [description, setDescription] = useState(DEFAULT_DESCRIPTION);
    const [exerciseType, setExerciseType] = useState("bodyweight_squat");
    const [purpose, setPurpose] = useState("training");
    const [primaryTarget, setPrimaryTarget] = useState("squat_quality");
    const [secondaryTarget, setSecondaryTarget] = useState("biomechanical_errors");
    const [isPreviewing, setIsPreviewing] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [importCompleted, setImportCompleted] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [outcomeMessage, setOutcomeMessage] = useState("");
    const isBusy = (() => isPreviewing || isImporting)();
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
    async function previewArchive() {
        if (isBusy)
            return;
        if (!zipFile) {
            setErrorMessage("Select a ZIP archive first.");
            return;
        }
        setIsPreviewing(true);
        setPreview(null);
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
            <p data-v-dataset-import-modal="" className={cx("section-hint")}>{" Supported formats: MP4, MOV, M4V, and AVI. Participant IDs and camera views come from manifest.csv. "}</p>
            <label data-v-dataset-import-modal="" htmlFor="dataset-archive" className={cx("file-picker")}><span data-v-dataset-import-modal="" aria-hidden="true" className={cx("file-picker-icon")}>{"↑"}</span>
            <strong data-v-dataset-import-modal="">{display(zipFile?.name || "Choose dataset ZIP")}</strong>
            <small data-v-dataset-import-modal="">{display(zipFile
                    ? `${(zipFile.size / 1024 / 1024).toFixed(1)} MB`
                    : "Select a ZIP archive containing your videos")}</small>
            <input data-v-dataset-import-modal="" id="dataset-archive" ref={zipInput} type="file" accept=".zip,application/zip" disabled={isBusy || importCompleted} onChange={handleFileChange}/></label>
            <p data-v-dataset-import-modal="" className={cx("section-hint")}>{" Include manifest.csv and the videos folder. All videos require annotation; good/bad filename tokens are not training labels. "}</p>
            <button data-v-dataset-import-modal="" type="button" disabled={!zipFile || isBusy || importCompleted} onClick={() => previewArchive()} className={cx("secondary-button preview-button")}>{display(isPreviewing ? "Inspecting archive..." : "Preview archive")}</button></section>
                {(preview) ? (<><section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"3. Review manifest"}</h3>
                <div data-v-dataset-import-modal="" className={cx("manifest-summary")}><div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Recognized videos"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.file_count)}</strong></div>
                <div data-v-dataset-import-modal=""><span data-v-dataset-import-modal="">{"Participants"}</span>
                <strong data-v-dataset-import-modal="">{display(preview.manifest.participant_count)}</strong></div>
                </div>
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
                <section data-v-dataset-import-modal="" className={cx("import-section")}><h3 data-v-dataset-import-modal="">{"4. Annotation"}</h3>
                <p data-v-dataset-import-modal="">{"All videos require annotation."}</p>
                <p data-v-dataset-import-modal="" className={cx("section-hint")}>{"Each segmented repetition receives human knee ratings. LOPO controls training and evaluation splits separately."}</p>
                <div data-v-dataset-import-modal="" className={cx("manifest-table-wrapper")}><table data-v-dataset-import-modal="" className={cx("manifest-table")}><thead data-v-dataset-import-modal=""><tr data-v-dataset-import-modal="">
                <th data-v-dataset-import-modal="">{"Participant"}</th>
                <th data-v-dataset-import-modal="">{"View"}</th>
                <th data-v-dataset-import-modal="">{"Review state"}</th>
                <th data-v-dataset-import-modal="">{"Archive path"}</th></tr></thead>
                <tbody data-v-dataset-import-modal="">{each(preview.manifest.files).map(([_index, file]) => (<tr data-v-dataset-import-modal="" key={file.archive_path}>
                    <td data-v-dataset-import-modal="">{display(file.participant_code)}</td>
                    <td data-v-dataset-import-modal="">{display(file.view_angle)}</td>
                    <td data-v-dataset-import-modal="">{"Required annotation"}</td>
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
