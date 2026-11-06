import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useEffect } from 'react';
import Transition from '../../Transition';
import { bindStyles } from '../../presentation';
import styles from './EvaluationModal.module.css';
interface Props {
    isOpen: boolean;
    datasetIds?: string[];
}
type Callbacks = {
    onClose?: () => void;
    onEvaluationStarted?: (payload: {
        evaluation_id: string;
    }) => void;
};
export default function EvaluationModal(input: Props & Callbacks) {
    const props = { ...{}, ...input };
    const { isOpen } = props;
    const cx = bindStyles(styles);
    type Emit = {
        (event: "close"): void;
        (event: "evaluation-started", payload: {
            evaluation_id: string;
        }): void;
    };
    const emit: Emit = ((event: string, ...args: unknown[]) => { switch (event) {
        case "close":
            props.onClose?.(...args as [
            ]);
            break;
        case "evaluation-started":
            props.onEvaluationStarted?.(...args as [
                payload: {
                    evaluation_id: string;
                }
            ]);
            break;
    } }) as Emit;
    const [selectedModel, setSelectedModel] = useState("model-v2-4");
    const [selectedDataset, setSelectedDataset] = useState("");
    const [batchSize, setBatchSize] = useState(32);
    const [confidenceThreshold, setConfidenceThreshold] = useState(0.85);
    const [isSubmitting, setIsSubmitting] = useState(false);
    useEffect(() => { setSelectedDataset(props.datasetIds?.[0] ?? 'ds-squat-benchmark-2026'); }, [props.datasetIds]);
    const handleClose = () => {
        emit("close");
    };
    const handleSubmit = async () => {
        if (isSubmitting)
            return;
        setIsSubmitting(true);
        try {
            await new Promise((resolve) => setTimeout(resolve, 600));
            const generatedId = `EVAL-JOB-${Math.floor(1000 + Math.random() * 9000)}`;
            emit("evaluation-started", { evaluation_id: generatedId });
            handleClose();
        }
        finally {
            setIsSubmitting(false);
        }
    };
    return (<>{createPortal(<><Transition name="modal-fade" classes={styles}>{(isOpen) ? (<div data-v-evaluation-modal="" onClick={(event) => { if (event.target !== event.currentTarget)
                return; handleClose(); }} className={cx("modal-backdrop")}><div data-v-evaluation-modal="" className={cx("modal-card")}><header data-v-evaluation-modal="" className={cx("modal-header")}><div data-v-evaluation-modal="" className={cx("modal-title-group")}><span data-v-evaluation-modal="" className={cx("modal-badge")}>{"EVALUATION JOB"}</span>
            <h2 data-v-evaluation-modal="">{"Launch New Evaluation"}</h2></div>
            <button data-v-evaluation-modal="" onClick={() => handleClose()} aria-label="Close modal" className={cx("close-btn")}>{" ✕ "}</button></header>
            <div data-v-evaluation-modal="" className={cx("modal-body")}><div data-v-evaluation-modal="" className={cx("form-group")}><label data-v-evaluation-modal="" className={cx("form-label")}>{"Target Model Checkpoint"}</label>
            <select data-v-evaluation-modal="" value={selectedModel ?? ''} onChange={(event) => setSelectedModel(event.target.value)} className={cx("form-select")}><option data-v-evaluation-modal="" value="model-v2-4">{" SquatVectorNet-v2.4 (ResNet3D Pose) "}</option>
            <option data-v-evaluation-modal="" value="model-v2-3">{" SquatVectorNet-v2.3 (MediaPipe Custom) "}</option>
            <option data-v-evaluation-modal="" value="model-v1-0">{" BaselineKinematics-v1 (Linear) "}</option></select></div>
            <div data-v-evaluation-modal="" className={cx("form-group")}><label data-v-evaluation-modal="" className={cx("form-label")}>{"Reference Validation Dataset"}</label>
            <select data-v-evaluation-modal="" value={selectedDataset ?? ''} onChange={(event) => setSelectedDataset(event.target.value)} className={cx("form-select")}><option data-v-evaluation-modal="" value="ds-squat-benchmark-2026">{" ds-squat-benchmark-2026 (1,240 frames) "}</option>
            <option data-v-evaluation-modal="" value="ds-valgus-testset-v2">{" ds-valgus-testset-v2 (850 frames) "}</option>
            <option data-v-evaluation-modal="" value="ds-kinematic-gold-standard">{" ds-kinematic-gold-standard (2,100 frames) "}</option></select></div>
            <div data-v-evaluation-modal="" className={cx("form-row")}><div data-v-evaluation-modal="" className={cx("form-group")}><label data-v-evaluation-modal="" className={cx("form-label")}>{"Inference Batch Size"}</label>
            <input data-v-evaluation-modal="" value={batchSize ?? ''} onChange={(event) => setBatchSize(Number(event.target.value))} type="number" min="1" max="128" className={cx("form-input")}/></div>
            <div data-v-evaluation-modal="" className={cx("form-group")}><label data-v-evaluation-modal="" className={cx("form-label")}>{"Keypoint Threshold"}</label>
            <input data-v-evaluation-modal="" value={confidenceThreshold ?? ''} onChange={(event) => setConfidenceThreshold(Number(event.target.value))} type="number" step="0.05" min="0.5" max="0.99" className={cx("form-input")}/></div></div>
            <div data-v-evaluation-modal="" className={cx("info-box")}><span data-v-evaluation-modal="" className={cx("info-icon")}>{"ℹ"}</span>
            <p data-v-evaluation-modal="" className={cx("info-text")}>{" Executing this run computes joint angle matrices and vector similarity scores against the benchmark ground truth. "}</p></div></div>
            <footer data-v-evaluation-modal="" className={cx("modal-footer")}><button data-v-evaluation-modal="" disabled={isSubmitting} onClick={() => handleClose()} className={cx("button secondary")}>{" Cancel "}</button>
            <button data-v-evaluation-modal="" disabled={isSubmitting || !selectedDataset || !selectedModel} onClick={() => handleSubmit()} className={cx("button primary")}>{(isSubmitting) ? (<span data-v-evaluation-modal="" className={cx("spinner")}></span>) : (<span data-v-evaluation-modal="">{"Start Evaluation Job"}</span>)}</button></footer></div></div>) : (null)}</Transition></>, document.body)}</>);
}
