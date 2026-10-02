"""result builder module to construct final analysis results and feedback"""


def build_result(metrics, classifications):
    result = {}

    result["metrics"] = metrics
    result["classifications"] = classifications
    result["feedback"] = build_feedback(classifications)

    return result


def build_feedback(classifications):
    feedback = []

    rom_result = classifications["rom"]
    asymmetry_result = classifications["asymmetry"]
    knee_result = classifications["knee_angle"]
    hip_result = classifications["hip_angle"]
    velocity_result = classifications["velocity"]

    if rom_result["classification"] == "insufficient":
        deficit = rom_result["evaluation"]["deficit"]

        feedback.append({
            "metric": "rom",
            "message": f"Your squat depth is insufficient. "
                       f"Your range of motion is {deficit:.1f} degrees below the required range."
        })

    if asymmetry_result["classification"] == "excessive":
        difference = asymmetry_result["evaluation"]["difference"]

        feedback.append({
            "metric": "asymmetry",
            "message": f"Excessive bilateral asymmetry was detected! "
                       f"Your asymmetry is {difference:.1f}% above the acceptable limit."
        })

    if knee_result["classification"] == "too_low":
        difference = knee_result["evaluation"]["difference"]

        feedback.append({
            "metric": "knee_angle",
            "message": f"Your knee angle is below the target range. "
                       f"It is {difference:.1f} degrees below the minimum target."
        })

    if knee_result["classification"] == "too_high":
        difference = knee_result["evaluation"]["difference"]

        feedback.append({
            "metric": "knee_angle",
            "message": f"Your knee angle is above the target range. "
                       f"It is {difference:.1f} degrees above the maximum target."
        })

    if hip_result["classification"] == "too_low":
        difference = hip_result["evaluation"]["difference"]

        feedback.append({
            "metric": "hip_angle",
            "message": f"Your hip angle is below the target range. "
                       f"It is {difference:.1f} degrees below the minimum target."
        })

    if hip_result["classification"] == "too_high":
        difference = hip_result["evaluation"]["difference"]

        feedback.append({
            "metric": "hip_angle",
            "message": f"Your hip angle is above the target range. "
                       f"It is {difference:.1f} degrees above the maximum target."
        })

    if velocity_result["classification"] == "too_slow":
        difference = velocity_result["evaluation"]["difference"]

        feedback.append({
            "metric": "velocity",
            "message": f"Your movement velocity is below the target range. "
                       f"Your velocity is {difference:.1f} m/s below the minimum target."
        })

    if velocity_result["classification"] == "too_fast":
        difference = velocity_result["evaluation"]["difference"]

        feedback.append({
            "metric": "velocity",
            "message": f"Your movement velocity was too fast. "
                       f"Your velocity is {difference:.1f} m/s above the maximum target."
        })

    return feedback
