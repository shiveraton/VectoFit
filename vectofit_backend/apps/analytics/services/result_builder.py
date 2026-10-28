"""result builder module to construct final analysis results and feedback"""


def build_result(metrics, classifications):
    result = {}

    result["metrics"] = metrics
    result["classifications"] = classifications
    result["feedback"] = build_feedback(classifications)

    return result


def build_feedback(classifications):
    feedback = []

    rom_result = classifications.get("rom", {})
    asymmetry_result = classifications.get("asymmetry", {})
    trunk_result = classifications.get("trunk_angle", {})
    knee_result = classifications.get("knee_angle", {})
    hip_result = classifications.get("hip_angle", {})
    velocity_result = classifications.get("velocity", {})

    if rom_result.get("classification") == "insufficient":
        evaluation = rom_result.get("evaluation", {})
        deficit = evaluation.get("deficit")

        if deficit is not None:
            feedback.append({
                "metric": "rom",
                "message": (
                    "Your squat depth is insufficient. "
                    f"Your range of motion is {deficit:.1f} degrees below the required range."
                ),
            })

    if asymmetry_result["classification"] == "excessive":
        evaluation = asymmetry_result.get("evaluation", {})
        difference = evaluation.get("difference")

        if difference is not None:
            feedback.append({
                "metric": "asymmetry",
                "message": ("Excessive bilateral asymmetry was detected! "
                        f"Your asymmetry is {difference:.1f}% above the acceptable limit."
                )
            })

    if trunk_result.get("classification") == "excessive_trunk_lean":
        evaluation = trunk_result.get("evaluation", {})
        difference = evaluation.get("difference")

        if difference is not None:
            feedback.append({
                "metric": "trunk_angle",
                "message": (
                    "Excessive trunk lean was detected! "
                    f"Your trunk lean is {difference:.1f}% above the configured arch limit."
                )
            })

    knee_classification = knee_result.get("classification")
    knee_evaluation = knee_result.get("evaluation", {})

    if knee_classification == "insufficient_depth":
        difference = knee_evaluation.get("difference")

        if difference is not None:
            feedback.append({
                "metric": "knee_angle",
                "message": (
                    "Your squat may not have reached the configured "
                    "depth target. Your minimum measured knee angke "
                    f"was {difference:.1f} degrees above the target."
                )
            })

    elif knee_classification == "too_low":
        difference = knee_evaluation.get("difference")

        if difference is not None:
            feedback.append({
                "metric": "knee_angle",
                "message": (
                    "Your knee angle was below the target range. "
                    f"It is {difference:.1f} degrees below the minimum target."
                )
            })

    hip_classification = hip_result.get("classification")
    hip_evaluation = hip_result.get("evaluation", {})

    if hip_classification in ("too_low", "too high"):
        difference = hip_evaluation.get("difference")

        if difference is not None:
            direction = (
                "below" if hip_classification == "too_low"
                else "above"
            )
            feedback.append({
                "metric": "hip_angle",
                "message": (
                    f"Your hip angle was {direction} the target range "
                    f"by {difference:.1f} degrees."
                )
            })

    velocity_classification = velocity_result.get("classification")
    velocity_evaluation = velocity_result.get("evaluation", {})

    if velocity_classification in ("too_slow", "too_fast"):
        difference = velocity_evaluation.get("difference")

        if difference is not None:
            description = (
                "too slow" if velocity_classification == "too_slow"
                else "too_fast"
            )
            feedback.append({
                "metric": "velocity",
                "message": (
                    f"Your movement velocity was {description} "
                    f"relative to the configured target by "
                    f"{difference:1f}."
                )
            })

    return feedback
