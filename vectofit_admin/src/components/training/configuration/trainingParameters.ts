export type ParameterSimulation =
  | "trees"
  | "depth"
  | "learning"
  | "split"
  | "seed";

export type TrainingParameterTarget =
  | "hyperparameter"
  | "testSize"
  | "randomSeed";

export interface TrainingParameterDefinition {
  key: string;
  target: TrainingParameterTarget;
  title: string;
  technicalName: string;
  question: string;
  description: string;
  min: number;
  max: number;
  step: number;
  lowLabel: string;
  highLabel: string;
  lowEffect: string;
  highEffect: string;
  recommended: string;
  defaultValue: number;
  simulation: ParameterSimulation;
  inputType: "range" | "number";
  format: "integer" | "decimal" | "percent";
}

export const TRAINING_PARAMETER_DEFINITIONS: TrainingParameterDefinition[] = [
  {
    key: "n_estimators",
    target: "hyperparameter",
    title: "Number of Trees",
    technicalName: "n_estimators",
    question: "How many decision trees should the model build?",
    description:
      "Controls how many trees are used in the XGBoost ensemble. More trees increase model capacity and training cost.",
    min: 10,
    max: 500,
    step: 10,
    lowLabel: "Fewer",
    highLabel: "More",
    lowEffect: "Smaller ensemble and faster training.",
    highEffect: "Larger ensemble with more model capacity.",
    recommended: "200",
    defaultValue: 200,
    simulation: "trees",
    inputType: "range",
    format: "integer",
  },
  {
    key: "max_depth",
    target: "hyperparameter",
    title: "Tree Complexity",
    technicalName: "max_depth",
    question: "How complex can each decision tree become?",
    description:
      "Controls the maximum depth of each tree. Deeper trees can learn more specific patterns but may fit noise.",
    min: 1,
    max: 10,
    step: 1,
    lowLabel: "Simpler",
    highLabel: "More detailed",
    lowEffect: "Simpler decision rules.",
    highEffect: "More detailed decision rules.",
    recommended: "4",
    defaultValue: 4,
    simulation: "depth",
    inputType: "range",
    format: "integer",
  },
  {
    key: "learning_rate",
    target: "hyperparameter",
    title: "Learning Rate",
    technicalName: "learning_rate",
    question: "How strongly should each new tree affect the model?",
    description:
      "Controls how much each successive tree contributes to the model.",
    min: 0.01,
    max: 0.5,
    step: 0.01,
    lowLabel: "Gradual",
    highLabel: "Aggressive",
    lowEffect: "Smaller updates to the model.",
    highEffect: "Larger updates from each tree.",
    recommended: "0.10",
    defaultValue: 0.1,
    simulation: "learning",
    inputType: "range",
    format: "decimal",
  },
  {
    key: "test_size",
    target: "testSize",
    title: "Test Set Size",
    technicalName: "test_size",
    question: "How much labelled data should be held out for testing?",
    description:
      "Controls the portion of labelled repetitions reserved for the held-out test set.",
    min: 0.1,
    max: 0.5,
    step: 0.05,
    lowLabel: "Smaller",
    highLabel: "Larger",
    lowEffect: "More data remains for training.",
    highEffect: "More data is reserved for testing.",
    recommended: "30%",
    defaultValue: 0.3,
    simulation: "split",
    inputType: "range",
    format: "percent",
  },
  {
    key: "random_seed",
    target: "randomSeed",
    title: "Random Seed",
    technicalName: "random_seed",
    question: "Which reproducible seed should this experiment use?",
    description:
      "Keeps the experiment reproducible when the same dataset and configuration are used again.",
    min: 0,
    max: 999999,
    step: 1,
    lowLabel: "Seed",
    highLabel: "Seed",
    lowEffect: "Identifies one reproducible experiment setup.",
    highEffect: "The value itself is not better or worse.",
    recommended: "42",
    defaultValue: 42,
    simulation: "seed",
    inputType: "number",
    format: "integer",
  },
];

export const FIXED_TRAINING_SETTINGS = [
  { label: "Objective", value: "binary:logistic" },
  { label: "Evaluation Metric", value: "logloss" },
  { label: "Split Strategy", value: "group_by_participant" },
];
