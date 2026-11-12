export type ParameterSimulation =
  | "trees"
  | "depth"
  | "learning"
  | "subsample"
  | "features"
  | "child-weight"
  | "regularization"
  | "split"
  | "seed";

export type TrainingParameterTarget = "hyperparameter";

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
    step: 1,
    lowLabel: "Fewer",
    highLabel: "More",
    lowEffect: "Smaller ensemble and faster training.",
    highEffect: "Larger ensemble with more model capacity.",
    recommended: "100",
    defaultValue: 100,
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
    max: 6,
    step: 1,
    lowLabel: "Simpler",
    highLabel: "More detailed",
    lowEffect: "Simpler decision rules.",
    highEffect: "More detailed decision rules.",
    recommended: "2",
    defaultValue: 2,
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
    max: 0.3,
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
];

export const FIXED_TRAINING_SETTINGS = [
  { label: "Evaluation", value: "Leave one participant out (LOPO)" },
];
