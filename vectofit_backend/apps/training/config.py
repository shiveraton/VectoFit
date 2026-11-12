import math

USER_HYPERPARAMETERS = {
    "n_estimators": (100, int, 10, 500),
    "learning_rate": (0.1, float, 0.01, 0.3),
    "max_depth": (2, int, 1, 6),
}

LOCKED_HYPERPARAMETERS = {
    "tree_method": "hist",
    "booster": "gbtree",
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "min_child_weight": 1,
    "reg_lambda": 1,
    "gamma": 0,
    "reg_alpha": 0,
    "seed": 42,
}


TASK_PROFILES = {
    "quality": {
        **LOCKED_HYPERPARAMETERS,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
    },
    "error_type": {
        **LOCKED_HYPERPARAMETERS,
        "objective": "multi:softprob",
        "eval_metric": "mlogloss",
    },
}

TARGET_TASK_PROFILES = {
    "binary_form": "quality",
    "knee_alignment": "quality",
    "error_type": "error_type",
}


def locked_hyperparameters(prediction_target, class_count):
    profile = TARGET_TASK_PROFILES[prediction_target]
    params = dict(TASK_PROFILES[profile])
    if profile == "error_type":
        params["num_class"] = class_count
    return params


def default_hyperparameters():
    return {
        name: spec[0] for name, 
        spec in USER_HYPERPARAMETERS.items()
    }


def validate_hyperparameters(values):
    unknown = sorted(set(values) - set(USER_HYPERPARAMETERS))
    if unknown:
        raise ValueError(
            f"Unsupported or fixed hyperparameter(s): {unknown}. "
            f"Editable parameters: {sorted(USER_HYPERPARAMETERS)}."
        )
    result = default_hyperparameters()
    
    for name, value in values.items():
        _, kind, minimum, maximum = USER_HYPERPARAMETERS[name]
        valid_type = isinstance(value, int) if kind is int else isinstance(value, (int, float))

        if isinstance(value, bool) or not valid_type or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"{name} must be a finite {kind.__name__}.")
        
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}.")
        result[name] = kind(value)
    return result
