"""classifier module to evaluate measurements and what they mean"""

import os
import numpy as np

def _not_evaluated(reason):
    return {
        "classification": "not_evaluated",
        "evaluation": {
            "reason": reason
        },
    }

def classify_metrics(metrics, thresholds):
    required_thresholds = {
        "knee_depth",
        "trunk_lean",
        "asymmetry"
    }

    missing = required_thresholds - set(thresholds.keys())
    if missing:
        raise ValueError(
            f"Missing exercise thresholds: {sorted(missing)}"
        )

    trunk_angles = metrics.get("trunk_angle")

    if not trunk_angles:
        raise ValueError(
            "Cannot evaluate trunk lean without trunk-angle measurements."
        )

    knee_angle = float(metrics["knee_angle"])
    maximum_trunk_lean = max(
        abs(float(angle)) for angle in trunk_angles
    )
    asymmetry = float(metrics["asymmetry"])

    knee_depth_threshold = float(thresholds["knee_depth"])
    trunk_lean_threshold = float(thresholds["trunk_lean"])
    asymmetry_threshold = float(thresholds["asymmetry"])

    knee_classification = (
        "insufficient_depth"
        if knee_angle > knee_depth_threshold
        else "acceptable"
    )

    trunk_classification = (
        "excessive_trunk_lean"
        if maximum_trunk_lean > trunk_lean_threshold
        else "acceptable"
    )

    return {
        "rom": _not_evaluated(
            "No minimum ROM threshold is configured for this exercise."
        ),
        "asymmetry": evaluate_asymmetry(
            asymmetry,
            asymmetry_threshold
        ),
        "trunk_angle": {
            "classification": trunk_classification,
            "evaluation": {
                "maximum_measured_lean_deg": maximum_trunk_lean,
                "maximum_allowed_lean_deg": trunk_lean_threshold,
                "difference": max(
                    0.0,
                    maximum_trunk_lean - trunk_lean_threshold
                ),
            },
        },
        "knee_angle": {
            "classification": knee_classification,
            "evaluation": {
                "measured_minimum_knee_angle_deg": knee_angle,
                "depth_threshold": knee_depth_threshold,
                "difference": max(
                    0.0,
                    knee_angle - knee_depth_threshold
                ),
            },
        },
        "hip_angle": _not_evaluated(
            "No hip-angle evaluation thresholds are configured."
        ),
        "velocity": _not_evaluated(
            "No velocity evaluation thresholds are configured."
        ),
    }

def evaluate_hip_angle(hip_angle, minimum_hip_angle, maximum_hip_angle):
    if hip_angle < minimum_hip_angle:
        classification = "too_low"
        difference = minimum_hip_angle - hip_angle
    elif hip_angle > maximum_hip_angle:
        classification = "too_high"
        difference = hip_angle - maximum_hip_angle
    else:
        classification = "acceptable"
        difference = 0

    return {
        "classification": classification,
        "evaluation": {
            "measured_hip_angle": hip_angle,
            "minimum_hip_angle": minimum_hip_angle,
            "maximum_hip_angle": maximum_hip_angle,
            "difference": difference,
        }
    }


def evaluate_velocity(velocity, minimum_velocity, maximum_velocity):
    if velocity < minimum_velocity:
        classification = "too_slow"
        difference = minimum_velocity - velocity
    elif velocity > maximum_velocity:
        classification = "too_fast"
        difference = velocity - maximum_velocity
    else:
        classification = "acceptable"
        difference = 0

    return {
        "classification": classification,
        "evaluation": {
            "measured_velocity": velocity,
            "minimum_velocity": minimum_velocity,
            "maximum_velocity": maximum_velocity,
            "difference": difference,
        }
    }


def evaluate_rom(rom, minimum_rom):
    deficit = minimum_rom - rom

    if deficit > 0:
        return {
            "classification": "insufficient",
            "evaluation": {
                "measured_rom": rom,
                "required_rom": minimum_rom,
                "deficit": deficit,
            }
        }

    return {
        "classification": "acceptable",
        "evaluation": {
            "measured_rom": rom,
            "required_rom": minimum_rom,
            "deficit": 0
        }
    }

def evaluate_asymmetry(asymmetry, maximum_asymmetry):

    if asymmetry <= maximum_asymmetry:
        classification = "acceptable"
    else:
        classification = "excessive"

    difference = asymmetry - maximum_asymmetry

    return {
        "classification": classification,
        "evaluation": {
            "measured_asymmetry": asymmetry,
            "maximum_asymmetry": maximum_asymmetry,
            "difference": max(difference, 0),
        }
    }

def evaluate_trunk_angle(trunk_angle, proper_trunk_form):
    results = {}

    deviation = np.abs(
        np.array(trunk_angle)
        - np.array(proper_trunk_form["reference_trajectory"])
    )

    natural_variability = np.array(
        proper_trunk_form["natural_variability"]
    )

    within_reference = deviation <= natural_variability

    within_percentage = (
        np.sum(within_reference) / len(within_reference)
    ) * 100

    # evaluate trajectory consistency
    user_changes = np.diff(np.array(trunk_angle))

    reference_changes = np.diff(
        np.array(proper_trunk_form["reference_trajectory"])
    )

    change_deviation = np.abs(user_changes - reference_changes)

    mean_change_deviation = np.mean(change_deviation)

    results["deviation"] = deviation
    results["within_reference"] = within_reference
    results["within_percentage"] = within_percentage
    results["change_deviation"] = change_deviation
    results["mean_change_deviation"] = mean_change_deviation

    return results

def evaluate_range(name, value, lo, hi, low_label, high_label):
    if value < lo:
        cls, diff = low_label, lo - value
    elif value > hi:
        cls, diff = high_label, value - hi
    else:
        cls, diff = "acceptable", 0.0
    return {
        "classification": cls,
        "evaluation": {
            f"measured_{name}": value, 
            "minimum": lo, 
            "maximum": hi, 
            "difference": diff
        }
    }

def evaluate_knee(knee, t):
    return {
        "flexion": evaluate_range(
            "knee_flexion", 
            knee["flexion"], 
            *t["flexion"],
            "excessive_depth",
            "insufficient_depth"
        ),
        "frontal": evaluate_range(
            "knee_frontal",
            knee["frontal"],
            *t["frontal"],
            "knee_varus",
            "knee_valgus"
        ),
    }
        

if __name__ == "__main__":

    trunk_angle = [
        12.0,
        12.5,
        13.0,
        13.5,
        14.0
    ]

    proper_trunk_form = {
        "reference_trajectory": [
            12.0,
            12.5,
            13.0,
            13.5,
            14.0
        ],
        "natural_variability": [
            0.5,
            0.6,
            0.5,
            0.7,
            0.6
        ]
    }

    results = evaluate_trunk_angle(
        trunk_angle,
        proper_trunk_form
    )

    print(results)
