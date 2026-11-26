import { useId } from "react";
import type { TrainingSplit } from "../../../services/trainingService";
import styles from "./SplitSelector.module.css";

type SplitSelectorProps = {
  value: TrainingSplit;
  onChange: (value: TrainingSplit) => void;
  testSize: number;
  onTestSizeChange: (value: number) => void;
  disabled?: boolean;
};

const splitOptions: {
  value: TrainingSplit;
  label: string;
  description: string;
}[] = [
  {
    value: "holdout",
    label: "HOLDOUT",
    description:
      "Reserve a group of participants for testing and train on the rest.",
  },
  {
    value: "leave_one_participant_out",
    label: "LOPO",
    description:
      "Test on one participant at a time and train on all other participants.",
  },
];

export default function SplitSelector({
  value,
  onChange,
  testSize,
  onTestSizeChange,
  disabled = false,
}: SplitSelectorProps) {
  const name = useId();

  return (
    <fieldset className={styles.selector} disabled={disabled}>
      <legend className={styles.title}>Training Split</legend>
      <p className={styles.description}>
        Choose how participants are split for training and testing.
      </p>
      <div className={styles.options}>
        {splitOptions.map((option) => (
          <label key={option.value} className={styles.option}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span className={styles.copy}>
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </span>
          </label>
        ))}
      </div>
      {value === "holdout" && (
        <label className={styles.testSize}>
          <span>Test participants: {Math.round(testSize * 100)}%</span>
          <input
            type="range"
            min={10}
            max={50}
            step={5}
            value={Math.round(testSize * 100)}
            onChange={(event) =>
              onTestSizeChange(Number(event.target.value) / 100)
            }
          />
          <span>
            Training {Math.round((1 - testSize) * 100)}% / Testing{" "}
            {Math.round(testSize * 100)}%
          </span>
        </label>
      )}
    </fieldset>
  );
}
