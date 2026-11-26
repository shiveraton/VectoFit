from math import isfinite

from django.db.models import Q

from apps.analytics.services.fppa import extract_fppa_features

SIDES = ("left", "right")
LANDMARKS = {
    "nose": "nose", "lShoulder": "left_shoulder", "rShoulder": "right_shoulder",
    "lHip": "left_hip", "rHip": "right_hip", "lKnee": "left_knee", "rKnee": "right_knee",
    "lAnkle": "left_ankle", "rAnkle": "right_ankle",
}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def measurement(rep):
    result = (rep.analysis_result or {}).get("fppa") or {}
    knees = result.get("knees") or {}
    if result.get("status") != "assessed" or not all(
        isinstance(knees.get(side), dict) and number(knees[side].get("peak_degrees"))
        and knees[side].get("state") in {"aligned", "deviation"} for side in SIDES
    ):
        return None
    return result


def model_evidence(rep, measured):
    model = (rep.analysis_result or {}).get("model_prediction") or {}
    probability = model.get("probability")
    if not (model.get("status") == "assessed" and model.get("prediction_target") == "knee_alignment"
            and model.get("view_angle", "frontal") == "frontal" and model.get("predicted_class") in {"good", "bad"}
            and number(probability) and 0 <= probability <= 1):
        return {"label": None, "confidence": None, "disagrees": None}
    deviation = any(measured["knees"][side]["state"] == "deviation" for side in SIDES) if measured else None
    return {"label": model["predicted_class"], "confidence": probability,
            "disagrees": None if deviation is None else (model["predicted_class"] == "bad") != deviation}


def normalized_points(entry, width, height):
    observed = entry.get("landmarks") or {}
    if not isinstance(observed, dict):
        return None
    points = {}
    for key, source in LANDMARKS.items():
        item = observed.get(source)
        visibility = (entry.get("visibility") or {}).get(source, 1.0)
        if not number(visibility) or visibility < 0.5:
            return None
        if isinstance(item, dict):
            x, y = item.get("x"), item.get("y")
            normalized = item.get("normalized", False)
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            x, y = item[:2]
            normalized = False
        else:
            return None
        if not number(x) or not number(y):
            return None
        if not normalized:
            x, y = x / width, y / height
        if not (0 <= x <= 1 and 0 <= y <= 1):
            return None
        points[key] = [x, y]
    return points


def rep_result(rep, mirrored):
    measured = measurement(rep)
    model = model_evidence(rep, measured)
    output = {
        "index": rep.rep_number, "status": "unassessable",
        "kneeStatus": {side: "unassessable" for side in SIDES},
        "reason": "low_tracking_confidence", "peakDeg": None, "worseKnee": None, "worstPeakDeg": None,
        "peakAtMs": None, "durationMs": None, "phases": None, "series": None, "offTrack": None, "frames": None,
        "modelEvidence": model, "insight": None,
        "reasonDetail": "Knee-angle measurements were unavailable for this rep, so it was left out of these results.",
    }
    if not measured:
        if ((rep.analysis_result or {}).get("fppa") or {}).get("reason") == "shorter_than_filter_window":
            output["reasonDetail"] = "This rep was too short for knee-angle analysis, so it was left out of these results."
        return output
    knees = measured["knees"]
    peaks = {side: knees[side]["peak_degrees"] for side in SIDES}
    worse = max(SIDES, key=lambda side: abs(peaks[side]))
    output.update({
        "status": "deviated" if any(knees[side]["state"] == "deviation" for side in SIDES) else "aligned",
        "kneeStatus": {side: "deviated" if knees[side]["state"] == "deviation" else "aligned" for side in SIDES},
        "peakDeg": peaks, "worseKnee": worse, "worstPeakDeg": peaks[worse],
        "kneeDirection": {side: ("inward" if peaks[side] > 0 else "outward")
                          if knees[side]["state"] == "deviation" else None for side in SIDES},
    })
    output.pop("reason")
    output["insight"] = "Both knees stayed in line through this rep." if output["status"] == "aligned" else (
        f"Your {worse} knee moved {knees[worse].get('direction') or ('inward' if peaks[worse] > 0 else 'outward')} during this rep."
    )
    entries = rep.landmark_series or []
    if len(entries) < 2 or not all(isinstance(entry, dict) and number(entry.get("timestamp_ms")) for entry in entries):
        return output
    times = [entry["timestamp_ms"] - entries[0]["timestamp_ms"] for entry in entries]
    if any(current <= previous for previous, current in zip(times, times[1:])):
        return output
    output["durationMs"] = times[-1]
    width, height, fps = (entries[0].get(key) for key in ("source_width", "source_height", "native_fps"))
    if not all(number(value) and value > 0 for value in (width, height, fps)):
        return output
    if mirrored is not None:
        frames = []
        for time, entry in zip(times, entries):
            points = normalized_points(entry, width, height)
            if points:
                frames.append({"tMs": time, "pts": points})
        output["frames"] = frames or None
    trace = measured.get("trace")
    if trace is None:
        try:
            _, metadata = extract_fppa_features(entries, frame_width=width, frame_height=height, native_fps=fps, include_trace=True)
            trace = metadata.get("trace")
        except (ValueError, TypeError, KeyError, ArithmeticError, IndexError, AttributeError):
            return output
    if not isinstance(trace, dict) or not all(isinstance(trace.get(side), list) and len(trace[side]) == len(times) for side in SIDES):
        return output
    
    if not all(all(number(value) for value in trace[side])
               and abs(max(trace[side], key=abs) - peaks[side]) < 1e-6 for side in SIDES):
        return output
    output["series"] = {"tMs": times, "leftDeg": trace["left"], "rightDeg": trace["right"]}
    peak_index = max(range(len(times)), key=lambda i: abs(trace[worse][i]))
    output["peakAtMs"] = times[peak_index]
    cutoff = measured.get("cutoff_degrees")
    if number(cutoff) and cutoff >= 0:
        windows = {}
        for side in SIDES:
            values = trace[side]
            peak = max(range(len(values)), key=lambda i: abs(values[i]))
            if abs(values[peak]) <= cutoff:
                continue
            first = last = peak
            while first > 0 and abs(values[first - 1]) > cutoff:
                first -= 1
            while last < len(values) - 1 and abs(values[last + 1]) > cutoff:
                last += 1
            windows[side] = {"startMs": times[first], "endMs": times[last]}
        output["offTrack"] = windows or None
    return output


def build_session_result(session):
    if session.status != "COMPLETED" or session.view_angle != "frontal":
        return None
    reps = [rep_result(rep, session.capture_mirrored) for rep in session.reps.all()]
    assessed = [rep for rep in reps if rep["status"] != "unassessable"]
    counts = {status: sum(rep["status"] == status for rep in reps) for status in ("aligned", "borderline", "deviated", "unassessable")}
    summary = {"totalReps": len(reps), "counts": counts, "assessableReps": len(assessed), "previousAlignedCount": None}
    for side in SIDES:
        summary[side] = {"status": "unassessable", "worstPeakDeg": None}
        if assessed:
            summary[side] = {
                "status": "deviated" if any(rep["kneeStatus"][side] == "deviated" for rep in assessed) else "aligned",
                "worstPeakDeg": max((rep["peakDeg"][side] for rep in assessed), key=abs),
            }
    summary["balanceDeg"] = abs(summary["right"]["worstPeakDeg"]) - abs(summary["left"]["worstPeakDeg"]) if assessed else None
    previous = type(session).objects.filter(user_id=session.user_id, exercise_variant_id=session.exercise_variant_id,
        view_angle="frontal", status="COMPLETED").filter(Q(created_at__lt=session.created_at)
        | Q(created_at=session.created_at, pk__lt=session.pk)).order_by("-created_at", "-pk").first()
    if previous:
        previous_measurements = [measurement(rep) for rep in previous.reps.only("analysis_result")]
        valid = [item for item in previous_measurements if item]
        if valid:
            summary["previousAlignedCount"] = sum(all(item["knees"][side]["state"] == "aligned" for side in SIDES) for item in valid)
    directions = {rep["kneeDirection"][side] for rep in assessed for side in SIDES if rep["kneeStatus"][side] == "deviated"}
    disagreement = any(rep["modelEvidence"]["disagrees"] for rep in reps)
    if not assessed:
        headline, cues = "We couldn't assess any reps", []
    elif not counts["deviated"]:
        headline, cues = "Both knees stayed in line for the measured reps.", ["Keep both knees tracking in line with your feet."]
    else:
        direction = next(iter(directions)) if len(directions) == 1 else "inward or outward"
        headline = f"Knee movement {direction} was measured on {counts['deviated']} of {len(reps)} reps."
        cues = [] if disagreement else ["Keep both knees tracking in line with your feet."]
    if disagreement:
        cues = []
    first_entry = next((entry for rep in session.reps.all() for entry in (rep.landmark_series or []) if isinstance(entry, dict)), {})
    width, height = first_entry.get("source_width"), first_entry.get("source_height")
    aspect = width / height if number(width) and number(height) and width > 0 and height > 0 else None
    return {
        "sessionId": str(session.pk), "recordedAt": session.created_at.isoformat(), "view": "front",
        "capture": {"mirrored": session.capture_mirrored, "aspectRatio": aspect},
        "signedAngles": True, "summary": summary, "reps": reps,
        "presentation": {"headline": headline, "cues": cues, "modelDisagreement": disagreement},
    }
