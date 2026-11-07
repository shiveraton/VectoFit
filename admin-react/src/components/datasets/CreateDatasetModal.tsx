import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useEffect } from 'react';
import type { ChangeEvent, Dispatch, SetStateAction } from 'react';
import { useDialogFocus } from "../../composables/useDialogFocus";
import type { CreateDatasetPayload } from "../../services/datasetService";
import type { Participant } from "../../services/participantService";
import { bindStyles, each, display } from '../../presentation';
import styles from './CreateDatasetModal.module.css';
type Callbacks = {
    onClose?: () => void;
    onSubmit?: () => void;
    onCreateParticipant?: () => void;
};
export default function CreateDatasetModal(input: {
    isOpen: boolean;
    isSubmitting: boolean;
    form: CreateDatasetPayload;
    participants: Participant[];
    onFormChange: Dispatch<SetStateAction<CreateDatasetPayload>>;
} & Callbacks) {
    const props = { ...{}, ...input };
    const { isOpen, isSubmitting, form, participants } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "close"): void;
        (event: "submit"): void;
        (event: "create-participant"): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "close":
            props.onClose?.(...args as [
            ]);
            break;
        case "submit":
            props.onSubmit?.(...args as [
            ]);
            break;
        case "create-participant":
            props.onCreateParticipant?.(...args as [
            ]);
            break;
    } }) as Emit;
    const dialogRef = useRef<HTMLElement | null>(null);
    useDialogFocus(() => props.isOpen, dialogRef);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const nameInputRef = useRef<HTMLInputElement | null>(null);
    const participantSelectRef = useRef<HTMLSelectElement | null>(null);
    const viewAngleSelectRef = useRef<HTMLSelectElement | null>(null);
    const [fileError, setFileError] = useState("");
    const [formError, setFormError] = useState("");
    const selectedFileName = (() => props.form.video_file?.name ?? "")();
    const canSubmit = (() => {
        return (!props.isSubmitting &&
            props.form.name.trim().length > 0 &&
            props.form.video_file !== null &&
            typeof props.form.participant === "number" &&
            [1, 2, 3].includes(props.form.view_angle ?? 0) &&
            !fileError);
    })();
    useEffect(() => {
        setFormError('');
        setFileError('');
        if (!props.isOpen) {
            props.onFormChange(previous => ({ ...previous, video_file: null }));
            if (fileInputRef.current)
                fileInputRef.current.value = '';
        }
    }, [props.isOpen]);
    const setForm = props.onFormChange;
    function closeModal() {
        if (props.isSubmitting)
            return;
        emit("close");
    }
    function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0] ?? null;
        setFileError("");
        setFormError("");
        props.onFormChange(previous => ({ ...previous, video_file: null }));
        if (!file)
            return;
        if (!file.name.toLowerCase().endsWith(".mp4")) {
            setFileError("Please select an MP4 video file.");
            input.value = "";
            return;
        }
        props.onFormChange(previous => ({ ...previous, video_file: file }));
    }
    function handleSubmit() {
        setFormError("");
        if (props.isSubmitting)
            return;
        if (!props.form.name.trim()) {
            setFormError("Enter a dataset name.");
            nameInputRef.current?.focus();
            return;
        }
        if (!props.form.video_file || fileError) {
            setFileError(fileError || "Select an MP4 video.");
            fileInputRef.current?.focus();
            return;
        }
        if (props.form.participant == null) {
            setFormError("Select a participant.");
            participantSelectRef.current?.focus();
            return;
        }
        if (![1, 2, 3].includes(props.form.view_angle ?? 0)) {
            setFormError("Select the video's view angle.");
            viewAngleSelectRef.current?.focus();
            return;
        }
        emit("submit");
    }
    return (<>{createPortal(<>{(isOpen) ? (<div data-v-create-dataset-modal="" onClick={(event) => { if (event.target !== event.currentTarget)
                return; closeModal(); }} onKeyDown={(event) => { if (event.key !== 'Escape')
                return; closeModal(); }} className={cx("modal-overlay")}><section data-v-create-dataset-modal="" ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="dataset-modal-title" className={cx("modal-card")}><header data-v-create-dataset-modal="" className={cx("modal-header")}><div data-v-create-dataset-modal=""><p data-v-create-dataset-modal="" className={cx("eyebrow")}>{"DATASET MANAGEMENT"}</p>
            <h2 data-v-create-dataset-modal="" id="dataset-modal-title">{"Create New Dataset"}</h2>
            <p data-v-create-dataset-modal="" className={cx("modal-description")}>{" Register a squat video for processing and analysis. "}</p></div>
            <button data-v-create-dataset-modal="" type="button" aria-label="Close dialog" disabled={isSubmitting} onClick={() => closeModal()} className={cx("close-btn")}>{" ✕ "}</button></header>
            <form data-v-create-dataset-modal="" onSubmit={(event) => { event.preventDefault(); handleSubmit(); }} className={cx("modal-body")}>{(formError) ? (<div data-v-create-dataset-modal="" role="alert" className={cx("form-error")}>{display(formError)}</div>) : (null)}
            <div data-v-create-dataset-modal="" className={cx("form-group")}><label data-v-create-dataset-modal="" htmlFor="dataset-name">{"Dataset Name "}
            <span data-v-create-dataset-modal="">{"*"}</span></label>
            <input data-v-create-dataset-modal="" id="dataset-name" ref={nameInputRef} value={form.name ?? ''} onChange={(event) => setForm(previous => ({ ...previous, name: event.target.value }))} type="text" placeholder="e.g. Squat_Rep_Landmarks_v1" autoComplete="off" required/></div>
            <div data-v-create-dataset-modal="" className={cx("form-group")}><label data-v-create-dataset-modal="" htmlFor="dataset-desc">{"Description"}</label>
            <textarea data-v-create-dataset-modal="" id="dataset-desc" value={form.description ?? ''} onChange={(event) => setForm(previous => ({ ...previous, description: event.target.value }))} rows={3} placeholder="Describe the data source and recording conditions."></textarea></div>
            <div data-v-create-dataset-modal="" className={cx("form-group")}><label data-v-create-dataset-modal="" htmlFor="dataset-video">{"Raw Exercise Video "}
            <span data-v-create-dataset-modal="">{"*"}</span></label>
            <label data-v-create-dataset-modal="" htmlFor="dataset-video" className={cx("file-picker", { 'file-picker-error': fileError })}><span data-v-create-dataset-modal="" aria-hidden="true" className={cx("file-icon")}>{"↑"}</span>
            <span data-v-create-dataset-modal="" className={cx("file-copy")}><strong data-v-create-dataset-modal="">{display(selectedFileName || "Choose an MP4 video")}</strong>
            <span data-v-create-dataset-modal="">{display(selectedFileName
                    ? "Video selected"
                    : "Select a video from your device")}</span></span>
            <span data-v-create-dataset-modal="" className={cx("browse-label")}>{"Browse"}</span></label>
            <input data-v-create-dataset-modal="" id="dataset-video" ref={fileInputRef} type="file" accept=".mp4,video/mp4" required onChange={handleFileChange} className={cx("native-file-input")}/>
            {(fileError) ? (<p data-v-create-dataset-modal="" role="alert" className={cx("field-error")}>{display(fileError)}</p>) : (<p data-v-create-dataset-modal="" className={cx("field-hint")}>{" MP4 format only. The backend will validate the uploaded file. "}</p>)}</div>
            <div data-v-create-dataset-modal="" className={cx("form-group")}><label data-v-create-dataset-modal="" htmlFor="dataset-participant">{"Participant "}
            <span data-v-create-dataset-modal="">{"*"}</span></label>
            <div data-v-create-dataset-modal="" className={cx("participant-row")}><select data-v-create-dataset-modal="" id="dataset-participant" ref={participantSelectRef} value={form.participant ?? ''} onChange={(event) => setForm(previous => ({ ...previous, participant: (event.target.value === "" ? null : Number(event.target.value)) }))} required><option data-v-create-dataset-modal="" value={''} disabled>{"Select participant"}</option>
            {each(participants).map(([_index, participant]) => (<option data-v-create-dataset-modal="" key={participant.id} value={participant.id}>{display(participant.participant_code)}</option>))}</select>
            <button data-v-create-dataset-modal="" type="button" title="Create participant" aria-label="Create participant" disabled={isSubmitting} onClick={() => { emit('create-participant'); }} className={cx("add-participant-button")}>{" + "}</button></div>
            {(participants.length === 0) ? (<p data-v-create-dataset-modal="" className={cx("field-hint")}>{" No participants available. Create a participant first. "}</p>) : (null)}</div>
            <div data-v-create-dataset-modal="" className={cx("form-group")}><label data-v-create-dataset-modal="" htmlFor="dataset-view-angle">{"View Angle "}
            <span data-v-create-dataset-modal="">{"*"}</span></label>
            <select data-v-create-dataset-modal="" id="dataset-view-angle" ref={viewAngleSelectRef} value={form.view_angle ?? ''} onChange={(event) => setForm(previous => ({ ...previous, view_angle: (event.target.value === "" ? null : Number(event.target.value)) }))} required><option data-v-create-dataset-modal="" value={''} disabled>{"Select the recording angle"}</option>
            <option data-v-create-dataset-modal="" value={1}>{"Diagonal / 45°"}</option>
            <option data-v-create-dataset-modal="" value={2}>{"Frontal"}</option>
            <option data-v-create-dataset-modal="" value={3}>{"Sagittal"}</option></select></div>
            <footer data-v-create-dataset-modal="" className={cx("modal-footer")}><button data-v-create-dataset-modal="" type="button" disabled={isSubmitting} onClick={() => closeModal()} className={cx("secondary-button")}>{" Cancel "}</button>
            <button data-v-create-dataset-modal="" type="submit" disabled={!canSubmit} className={cx("primary-button")}>{(isSubmitting) ? (<span data-v-create-dataset-modal="" aria-hidden="true" className={cx("spinner")}></span>) : (null)}
            {" "}
            {display(isSubmitting ? "Creating dataset..." : "Create Dataset")}</button></footer></form></section></div>) : (null)}</>, document.body)}</>);
}
