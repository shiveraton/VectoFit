"""
VectoFit manual dataset annotator (Tkinter, installer-style white UI).

Shows one segmented repetition at a time (looping) and lets a human assign
ground truth from six Pass/Fail criteria. No model predictions are shown, so
ground truth stays uncontaminated.

Orientation
-----------
Phones store portrait videos as sideways pixels plus a rotation flag. The video
is rotated upright here from that flag. MediaPipe landmarks are produced on the
*unrotated* frames by default (--landmarks raw), so the stored coordinates are
rotated with the exact same transform before drawing. Use --landmarks upright
only if your pipeline already ran on upright frames.

Keys: SPACE play/pause | LEFT/RIGHT step | [ ] speed | 1-6 criteria | ENTER save
Requires: pip install pillow
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tkinter as tk
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Any

# ---------------------------------------------------------------------------
# Django bootstrap
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageTk  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.analytics.utils.file_resolver import resolved_video_path  # noqa: E402
from apps.datasets.models import Dataset, DatasetSample  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VIDEO_W, VIDEO_H = 800, 520  # display box; video is letterboxed inside it
MAX_SIDE = 1280              # longest side kept in memory (aspect preserved)
SPEEDS = [0.20, 0.35, 0.50, 0.75, 1.00, 1.50, 2.00]
DEFAULT_SPEED = 3

# key, title, suggested error label when FAIL (rename to your taxonomy)
CRITERIA = [
    ("depth", "Depth", "insufficient_depth"),
    ("knee", "Knee", "knee_valgus"),
    ("trunk", "Trunk", "excessive_trunk_lean"),
    ("symmetry", "Symmetry", "asymmetry"),
    ("foot", "Foot", "foot_instability"),
    ("completion", "Completion", "incomplete_rep"),
]

EDGES = [
    ("left_shoulder", "right_shoulder"), ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"), ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"), ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"), ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"), ("left_ankle", "left_heel"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"), ("right_ankle", "right_heel"),
]
JOINTS = sorted({j for edge in EDGES for j in edge})

ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}

# Palette
WHITE, CARD, BORDER, TEXT, MUTED = "#FFFFFF", "#F9FAFB", "#E5E7EB", "#111827", "#6B7280"
ACCENT, ACCENT_DARK, WARN = "#2563EB", "#1D4ED8", "#B45309"
PASS_BG, PASS_FG, FAIL_BG, FAIL_FG = "#DCFCE7", "#166534", "#FEE2E2", "#991B1B"
IDLE_BG, IDLE_FG = "#F3F4F6", "#6B7280"

FONT_FAMILY = "Helvetica"

# True once DatasetSample has `criteria = models.JSONField(null=True, blank=True)`
HAS_CRITERIA_FIELD = any(f.name == "criteria" for f in DatasetSample._meta.get_fields())


def font(size: int, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


# ---------------------------------------------------------------------------
# Rubric helpers
# ---------------------------------------------------------------------------

def verdict_of(criteria: dict[str, bool | None]) -> str:
    values = [criteria[k] for k, _, _ in CRITERIA]
    if any(v is False for v in values):
        return "INCORRECT"
    return "CORRECT" if all(v is True for v in values) else "PENDING"


def suggested_labels(criteria: dict[str, bool | None]) -> str:
    return ",".join(lbl for k, _, lbl in CRITERIA if criteria[k] is False)


def normalize_labels(raw: str) -> str:
    """'a, b ,,a' -> 'a,b' (strip, drop empties, de-duplicate in order)."""
    parts: list[str] = []
    for part in (p.strip() for p in raw.split(",")):
        if part and part not in parts:
            parts.append(part)
    return ",".join(parts)


def label_text(value: bool | None) -> str:
    return "CORRECT" if value is True else "INCORRECT" if value is False else "UNLABELLED"


# ---------------------------------------------------------------------------
# Landmarks: parsing and orientation-aware mapping
# ---------------------------------------------------------------------------

def read_xy(value: Any) -> tuple[float, float] | None:
    """Accept [x, y] or {x, y} / {x_coordinate, y_coordinate}."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        pair = (value[0], value[1])
    elif isinstance(value, dict):
        pair = (value.get("x_coordinate", value.get("x")),
                value.get("y_coordinate", value.get("y")))
    else:
        return None
    try:
        return float(pair[0]), float(pair[1])
    except (TypeError, ValueError):
        return None


def landmark_lookup(series: list[Any] | None, start_frame: int) -> dict[int, dict[str, tuple]]:
    """frame_index -> {joint: (x, y)} as stored (not yet transformed)."""
    out: dict[int, dict[str, tuple]] = {}
    for offset, entry in enumerate(series or []):
        if not isinstance(entry, dict):
            continue
        named = entry["landmarks"] if isinstance(entry.get("landmarks"), dict) else entry
        frame = entry["frame_index"] if isinstance(entry.get("frame_index"), int) else start_frame + offset
        out[frame] = {j: xy for j in JOINTS if (xy := read_xy(named.get(j))) is not None}
    return out


def to_display(xy: tuple[float, float], space: tuple, rotation: int,
               lm_in: str, out_w: int, out_h: int) -> tuple[int, int]:
    """
    Map a stored landmark onto the displayed (upright, downscaled) frame.

    1. Normalise by the landmark coordinate space (0-1 in the frame the pose
       model saw). Normalising makes the pipeline's own resize irrelevant.
    2. If landmarks came from the unrotated frames, rotate (u, v) exactly the
       way cv2.rotate rotated the pixels.
    3. Scale to the displayed frame size.
    """
    kind, lw, lh = space
    u, v = xy if kind == "norm" else (xy[0] / lw, xy[1] / lh)
    if lm_in == "raw":
        u, v = {0: (u, v), 90: (1 - v, u), 180: (1 - u, 1 - v), 270: (v, 1 - u)}[rotation]
    return int(round(u * out_w)), int(round(v * out_h))


def draw_pose(frame, pts: dict[str, tuple], space: tuple, rotation: int, lm_in: str) -> None:
    if not pts:
        return
    h, w = frame.shape[:2]
    thick = max(2, min(h, w) // 240)
    xy = {j: to_display(p, space, rotation, lm_in, w, h) for j, p in pts.items()}
    for a, b in EDGES:
        if a in xy and b in xy:
            cv2.line(frame, xy[a], xy[b], (255, 200, 0), thick, cv2.LINE_AA)
    for p in xy.values():
        cv2.circle(frame, p, thick + 3, (0, 255, 255), -1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Video: rotation and frame loading
# ---------------------------------------------------------------------------

def resolve_rotation(cap, override: int | None) -> tuple[int, str]:
    """Clockwise degrees (0/90/180/270) that make frames upright."""
    auto_prop = getattr(cv2, "CAP_PROP_ORIENTATION_AUTO", None)
    meta_prop = getattr(cv2, "CAP_PROP_ORIENTATION_META", None)
    if auto_prop is not None:
        cap.set(auto_prop, 0)  # we rotate ourselves, identically on every build

    if override is not None:
        return override, f"manual --rotate {override}"
    if meta_prop is None:
        return 0, "this OpenCV cannot read rotation metadata (use --rotate)"

    degrees = int(round(cap.get(meta_prop) or 0)) % 360
    if degrees not in ROTATE_CODES:
        return 0, f"metadata {degrees} -> no rotation"

    # If the backend rotated frames anyway, don't rotate twice.
    rw, rh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ok, probe = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    if ok and rw != rh and probe.shape[:2] == (rw, rh):
        return 0, f"metadata {degrees}, but backend already rotated -> no rotation"
    return degrees, f"metadata {degrees} -> rotating {degrees} deg clockwise"


def read_frames(cap, start: int, end: int, rotation: int) -> list[tuple[int, Any]]:
    frames = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    for index in range(start, end + 1):
        ok, frame = cap.read()
        if not ok:
            break
        if rotation:
            frame = cv2.rotate(frame, ROTATE_CODES[rotation])
        scale = min(1.0, MAX_SIDE / max(frame.shape[:2]))
        if scale < 1.0:  # downscale only, aspect ratio preserved
            frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        frames.append((index, frame))
    return frames


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_annotation(sample, annotator, is_correct: bool | None, error_label: str,
                    criteria: dict[str, bool | None]) -> None:
    labelled = is_correct is not None
    with transaction.atomic():
        sample.is_correct = is_correct
        sample.error_label = error_label.strip() if labelled else ""
        sample.annotator = annotator if labelled else None
        sample.annotated_at = timezone.now() if labelled else None
        fields = ["is_correct", "error_label", "annotator", "annotated_at"]
        if HAS_CRITERIA_FIELD:
            sample.criteria = dict(criteria)
            fields.append("criteria")
        sample.save(update_fields=fields)


class Audit:
    """Append-only JSON log of every labelling action."""

    def __init__(self, path: Path):
        self.path = path
        self.entries: list[dict[str, Any]] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.entries = data if isinstance(data, list) else []
            except (OSError, json.JSONDecodeError):
                pass

    def last_criteria(self) -> dict[int, dict[str, bool | None]]:
        return {e["sample_id"]: dict(e["criteria"]) for e in self.entries
                if e.get("criteria") and e.get("sample_id") is not None}

    def add(self, sample, annotator_name: str, action: str, criteria: dict) -> None:
        rep = sample.rep_assessment
        self.entries.append({
            "timestamp_utc": timezone.now().isoformat(),
            "dataset_id": sample.dataset_id, "sample_id": sample.id,
            "rep_number": rep.rep_number, "start_frame": rep.start_frame,
            "end_frame": rep.end_frame, "action": action,
            "is_correct": sample.is_correct, "error_label": sample.error_label,
            "criteria": dict(criteria), "annotator": annotator_name,
        })
        self.path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

class FlatButton(tk.Label):
    """Label-based button so it looks identical on Windows/macOS/Linux."""

    def __init__(self, parent, text, command, primary=False):
        super().__init__(parent, text=text, padx=18, pady=8, bd=0, font=font(10, True))
        self.command, self.primary, self.enabled = command, primary, True
        self.bind("<Button-1>", lambda e: self.enabled and self.command())
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self._paint()

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        self._paint()

    def _paint(self, hover: bool = False) -> None:
        if not self.enabled:
            self.config(bg=BORDER, fg="#9CA3AF", highlightthickness=0, cursor="arrow")
        elif self.primary:
            self.config(bg=ACCENT_DARK if hover else ACCENT, fg=WHITE,
                        highlightthickness=0, cursor="hand2")
        else:
            self.config(bg=IDLE_BG if hover else WHITE, fg=TEXT, highlightthickness=1,
                        highlightbackground=BORDER, cursor="hand2")


class SegToggle(tk.Frame):
    """Pass / Fail segmented control; clicking the active side unsets it."""

    def __init__(self, parent, on_change):
        super().__init__(parent, bg=CARD)
        self.value: bool | None = None
        self.on_change = on_change
        self.labels = {}
        for val, text in ((True, "Pass"), (False, "Fail")):
            lbl = tk.Label(self, text=text, width=7, pady=5, font=font(10, True), cursor="hand2")
            lbl.pack(side="left", padx=(0, 6))
            lbl.bind("<Button-1>", lambda e, v=val: self.click(v))
            self.labels[val] = lbl
        self.set(None)

    def click(self, val: bool) -> None:
        self.set(None if self.value is val else val)
        self.on_change()

    def cycle(self) -> None:
        self.set({None: True, True: False, False: None}[self.value])
        self.on_change()

    def set(self, value: bool | None) -> None:
        self.value = value
        styles = {True: (PASS_BG, PASS_FG), False: (FAIL_BG, FAIL_FG)}
        for val, lbl in self.labels.items():
            bg, fg = styles[val] if value is val else (IDLE_BG, IDLE_FG)
            lbl.config(bg=bg, fg=fg)


def text_label(parent, text="", size=10, bold=False, fg=TEXT, bg=WHITE, **kw) -> tk.Label:
    return tk.Label(parent, text=text, font=font(size, bold), fg=fg, bg=bg, **kw)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

@dataclass
class Session:
    dataset: Any
    samples: list
    annotator: Any
    cap: Any
    fps: float
    audit: Audit
    rotation: int
    lm_space: tuple
    lm_in: str
    start_index: int
    show_pose: bool


class AnnotatorApp:
    def __init__(self, root: tk.Tk, session: Session):
        self.root, self.s = root, session
        self.index = session.start_index
        self.speed_i = DEFAULT_SPEED
        self.show_pose = tk.BooleanVar(value=session.show_pose)
        self.audit_criteria = session.audit.last_criteria()

        self.frames: list = []
        self.landmarks: dict = {}
        self.criteria: dict[str, bool | None] = {}
        self.pos, self.playing = 0, True
        self._job = None
        self._syncing_scale = False
        self._diag_done = False
        self.error_dirty = False

        root.report_callback_exception = self._on_error
        self._build()
        self.load_rep()

    # ---- layout ----------------------------------------------------------

    def _build(self) -> None:
        r, ds = self.root, self.s.dataset
        r.title("VectoFit Annotator")
        r.configure(bg=WHITE)
        r.geometry("1260x870")
        r.minsize(1260, 870)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Thin.Horizontal.TProgressbar", troughcolor=BORDER, background=ACCENT,
                        bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT, thickness=4)
        style.configure("Seek.Horizontal.TScale", background=WHITE, troughcolor=BORDER,
                        bordercolor=WHITE, lightcolor=WHITE, darkcolor=WHITE)

        header = tk.Frame(r, bg=WHITE)
        header.pack(fill="x", padx=32, pady=(22, 14))
        title = tk.Frame(header, bg=WHITE)
        title.pack(side="left")
        text_label(title, "VectoFit Annotator", 20, True).pack(anchor="w")
        text_label(title, f"Dataset {ds.pk} · {ds.name} · Participant {ds.participant_id}",
                   fg=MUTED).pack(anchor="w", pady=(2, 0))
        self.rep_label = text_label(header, size=12, bold=True, fg=ACCENT)
        self.rep_label.pack(side="right")
        self.progress = ttk.Progressbar(r, style="Thin.Horizontal.TProgressbar",
                                        maximum=len(self.s.samples))
        self.progress.pack(fill="x")

        footer = tk.Frame(r, bg=WHITE)
        footer.pack(side="bottom", fill="x")
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x")
        bar = tk.Frame(footer, bg=WHITE)
        bar.pack(fill="x", padx=32, pady=14)
        FlatButton(bar, "Back", lambda: self.go(-1)).pack(side="left")
        FlatButton(bar, "Clear", self.clear).pack(side="left", padx=(10, 0))
        FlatButton(bar, "Skip", lambda: self.go(1)).pack(side="left", padx=(10, 0))
        self.save_btn = FlatButton(bar, "Save & Next", self.save, primary=True)
        self.save_btn.pack(side="right")
        text_label(bar, "Space play/pause  ·  ←/→ step  ·  1-6 criteria  ·  Enter save",
                   9, fg=MUTED).pack(side="right", padx=20)

        body = tk.Frame(r, bg=WHITE)
        body.pack(fill="both", expand=True, padx=32, pady=20)
        self._build_video(body)
        self._build_card(body)
        self._bind_keys()

    def _build_video(self, body: tk.Frame) -> None:
        col = tk.Frame(body, bg=WHITE)
        col.pack(side="left", anchor="n")
        border = tk.Frame(col, bg=BORDER, padx=1, pady=1)
        border.pack()
        self.canvas = tk.Canvas(border, width=VIDEO_W, height=VIDEO_H, bg=TEXT, highlightthickness=0)
        self.canvas.pack()
        self._img_item = self.canvas.create_image(0, 0, anchor="nw")

        ctrl = tk.Frame(col, bg=WHITE)
        ctrl.pack(fill="x", pady=(14, 0))
        self.play_btn = FlatButton(ctrl, "Pause", self.toggle_play)
        self.play_btn.pack(side="left")
        FlatButton(ctrl, "‹", lambda: self.step(-1)).pack(side="left", padx=(8, 0))
        FlatButton(ctrl, "›", lambda: self.step(1)).pack(side="left", padx=(6, 0))
        self.scale = ttk.Scale(ctrl, from_=0, to=1, style="Seek.Horizontal.TScale",
                               command=self._on_seek)
        self.scale.pack(side="left", fill="x", expand=True, padx=16)
        self.pos_label = text_label(ctrl, size=9, fg=MUTED, width=22, anchor="e")
        self.pos_label.pack(side="left")

        opts = tk.Frame(col, bg=WHITE)
        opts.pack(fill="x", pady=(12, 0))
        text_label(opts, "Speed", fg=MUTED).pack(side="left")
        FlatButton(opts, "−", lambda: self.change_speed(-1)).pack(side="left", padx=(10, 6))
        self.speed_label = text_label(opts, bold=True, width=6)
        self.speed_label.pack(side="left")
        FlatButton(opts, "+", lambda: self.change_speed(1)).pack(side="left", padx=(6, 0))
        tk.Checkbutton(opts, text="Show pose overlay", variable=self.show_pose, command=self.render,
                       font=font(10), bg=WHITE, fg=TEXT, activebackground=WHITE,
                       selectcolor=WHITE, bd=0, highlightthickness=0).pack(side="right")

    def _build_card(self, body: tk.Frame) -> None:
        border = tk.Frame(body, bg=BORDER, padx=1, pady=1)
        border.pack(side="left", fill="both", expand=True, padx=(28, 0))
        inner = tk.Frame(border, bg=CARD)
        inner.pack(fill="both", expand=True, ipadx=24, ipady=22)

        def line():
            tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=16)

        text_label(inner, "Assessment", 14, True, bg=CARD).pack(anchor="w")
        text_label(inner, "Mark each criterion Pass or Fail.", fg=MUTED, bg=CARD).pack(
            anchor="w", pady=(2, 14))

        self.toggles: dict[str, SegToggle] = {}
        for n, (key, title, _) in enumerate(CRITERIA, 1):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill="x", pady=5)
            text_label(row, str(n), 9, True, MUTED, CARD, width=2).pack(side="left")
            text_label(row, title, 11, bg=CARD, width=11, anchor="w").pack(side="left")
            self.toggles[key] = SegToggle(row, self.on_criteria_change)
            self.toggles[key].pack(side="right")

        line()
        text_label(inner, "Error label(s)", 11, True, bg=CARD).pack(anchor="w")
        self.error_var = tk.StringVar()
        self.error_entry = tk.Entry(inner, textvariable=self.error_var, font=font(11), bd=0,
                                    bg=WHITE, fg=TEXT, insertbackground=TEXT, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT)
        self.error_entry.pack(fill="x", ipady=7, pady=(6, 4))
        self.error_entry.bind("<KeyRelease>", lambda e: setattr(self, "error_dirty", True))
        text_label(inner, "Auto-filled from failed criteria. Comma-separate; add others freely.",
                   9, fg=MUTED, bg=CARD, wraplength=320, justify="left").pack(anchor="w")

        line()
        row = tk.Frame(inner, bg=CARD)
        row.pack(fill="x")
        text_label(row, "Final label", 11, True, bg=CARD).pack(side="left")
        self.badge = tk.Label(row, font=font(10, True), padx=14, pady=5)
        self.badge.pack(side="right")
        self.saved_label = text_label(inner, size=9, fg=MUTED, bg=CARD)
        self.saved_label.pack(anchor="w", pady=(14, 0))
        self.status = text_label(inner, bold=True, fg=WARN, bg=CARD, wraplength=320, justify="left")
        self.status.pack(anchor="w", pady=(6, 0))

    def _bind_keys(self) -> None:
        r = self.root

        def guard(fn):  # ignore shortcuts while typing in the error box
            return lambda e: None if isinstance(r.focus_get(), tk.Entry) else fn()

        r.bind("<space>", guard(self.toggle_play))
        r.bind("<Left>", guard(lambda: self.step(-1)))
        r.bind("<Right>", guard(lambda: self.step(1)))
        r.bind("<bracketleft>", guard(lambda: self.change_speed(-1)))
        r.bind("<bracketright>", guard(lambda: self.change_speed(1)))
        r.bind("<Return>", lambda e: self.save())
        for n, (key, _, _) in enumerate(CRITERIA, 1):
            r.bind(str(n), guard(self.toggles[key].cycle))
        r.bind("<Button-1>", lambda e: r.focus_set() if e.widget is not self.error_entry else None,
               add="+")

    # ---- rep loading -----------------------------------------------------

    def load_rep(self) -> None:
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None

        sample = self.s.samples[self.index]
        rep = sample.rep_assessment
        self.frames = read_frames(self.s.cap, int(rep.start_frame), int(rep.end_frame),
                                  self.s.rotation)
        if not self.frames:
            self.set_status(f"Could not read frames for rep {rep.rep_number}; skipped.")
            self.go(1)
            return

        self.landmarks = landmark_lookup(rep.landmark_series, int(rep.start_frame))
        self._print_landmark_diagnostics(rep.rep_number)

        saved = (getattr(sample, "criteria", None) if HAS_CRITERIA_FIELD else None) \
            or self.audit_criteria.get(sample.pk, {})
        self.criteria = {key: saved.get(key) for key, _, _ in CRITERIA}
        for key, tog in self.toggles.items():
            tog.set(self.criteria[key])

        if sample.is_correct is False and sample.error_label:
            self.error_var.set(sample.error_label)
            self.error_dirty = True
        else:
            self.error_var.set(suggested_labels(self.criteria))
            self.error_dirty = False

        self.pos, self.playing = 0, True
        self.play_btn.config(text="Pause")
        self.scale.config(to=max(1, len(self.frames) - 1))
        self.rep_label.config(text=f"Repetition {self.index + 1} of {len(self.s.samples)}")
        self.speed_label.config(text=f"{SPEEDS[self.speed_i]:.2f}×")
        self.saved_label.config(text=f"Currently saved: {label_text(sample.is_correct)}")
        self.set_status("")
        self.refresh_verdict()
        self.refresh_progress()
        self.render()
        self.schedule()

    def _print_landmark_diagnostics(self, rep_number: int) -> None:
        """Once per session: show the real coordinate range so the space can be verified."""
        if self._diag_done:
            return
        self._diag_done = True
        pts = [p for frame in self.landmarks.values() for p in frame.values()]
        if not pts:
            print(f"[landmarks] rep {rep_number}: none found (is landmark_series empty?)")
            return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        print(f"[landmarks] rep {rep_number}: x {min(xs):.2f}..{max(xs):.2f}, "
              f"y {min(ys):.2f}..{max(ys):.2f} | declared space {self.s.lm_space} | "
              f"landmarks are in {self.s.lm_in} frames")

    # ---- playback --------------------------------------------------------

    def schedule(self) -> None:
        if self._job:
            self.root.after_cancel(self._job)
        delay = max(1, int(1000 / max(1.0, self.s.fps * SPEEDS[self.speed_i])))
        self._job = self.root.after(delay, self._tick)

    def _tick(self) -> None:
        self._job = None
        if self.playing:
            self.pos = (self.pos + 1) % len(self.frames)
            self.render()
            self.schedule()

    def _pause(self) -> None:
        self.playing = False
        self.play_btn.config(text="Play")

    def toggle_play(self) -> None:
        self.playing = not self.playing
        self.play_btn.config(text="Pause" if self.playing else "Play")
        if self.playing:
            self.schedule()

    def step(self, delta: int) -> None:
        self._pause()
        self.pos = max(0, min(len(self.frames) - 1, self.pos + delta))
        self.render()

    def _on_seek(self, value: str) -> None:
        if not self._syncing_scale:
            self._pause()
            self.pos = max(0, min(len(self.frames) - 1, int(float(value))))
            self.render(sync_scale=False)

    def change_speed(self, delta: int) -> None:
        self.speed_i = max(0, min(len(SPEEDS) - 1, self.speed_i + delta))
        self.speed_label.config(text=f"{SPEEDS[self.speed_i]:.2f}×")

    def render(self, sync_scale: bool = True) -> None:
        if not self.frames:
            return
        frame_index, frame = self.frames[self.pos]
        img = frame.copy()
        if self.show_pose.get():
            draw_pose(img, self.landmarks.get(frame_index, {}), self.s.lm_space,
                      self.s.rotation, self.s.lm_in)

        h, w = img.shape[:2]
        scale = min(VIDEO_W / w, VIDEO_H / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        img = cv2.cvtColor(cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2RGB)
        box = np.full((VIDEO_H, VIDEO_W, 3), (17, 24, 39), dtype=np.uint8)
        y0, x0 = (VIDEO_H - nh) // 2, (VIDEO_W - nw) // 2
        box[y0:y0 + nh, x0:x0 + nw] = img
        self._photo = ImageTk.PhotoImage(Image.fromarray(box))
        self.canvas.itemconfig(self._img_item, image=self._photo)

        self.pos_label.config(text=f"Frame {frame_index} · {self.pos + 1}/{len(self.frames)}")
        if sync_scale:
            self._syncing_scale = True
            self.scale.set(self.pos)
            self._syncing_scale = False

    # ---- criteria / verdict ----------------------------------------------

    def on_criteria_change(self) -> None:
        self.criteria = {key: tog.value for key, tog in self.toggles.items()}
        if not self.error_dirty:
            self.error_var.set(suggested_labels(self.criteria))
        self.set_status("")
        self.refresh_verdict()

    def refresh_verdict(self) -> None:
        verdict = verdict_of(self.criteria)
        bg, fg = {"CORRECT": (PASS_BG, PASS_FG), "INCORRECT": (FAIL_BG, FAIL_FG)}.get(
            verdict, (IDLE_BG, IDLE_FG))
        self.badge.config(text=verdict, bg=bg, fg=fg)
        self.save_btn.set_enabled(verdict != "PENDING")

    def refresh_progress(self) -> None:
        self.progress["value"] = sum(1 for s in self.s.samples if s.is_correct is not None)

    def set_status(self, text: str) -> None:
        self.status.config(text=text)

    # ---- actions ---------------------------------------------------------

    def _commit(self, is_correct: bool | None, error_label: str, action: str) -> None:
        sample = self.s.samples[self.index]
        save_annotation(sample, self.s.annotator, is_correct, error_label, self.criteria)
        sample.refresh_from_db()
        self.s.audit.add(sample, self.s.annotator.username, action, self.criteria)

    def save(self) -> None:
        verdict = verdict_of(self.criteria)
        if verdict == "PENDING":
            self.set_status("Assess all 6 criteria first.")
            return
        try:
            if verdict == "CORRECT":
                self._commit(True, "", "label_correct")
            else:
                labels = normalize_labels(self.error_var.get())
                self.error_var.set(labels)
                self._commit(False, labels, "label_incorrect")
        except Exception as exc:
            traceback.print_exc()
            try:
                self.s.samples[self.index].refresh_from_db()  # drop unsaved in-memory values
            except Exception:
                pass
            self.set_status(f"Save failed: {type(exc).__name__}: {exc}")
            messagebox.showerror("Save failed", f"{type(exc).__name__}: {exc}")
            return
        self.refresh_progress()
        self.go(1)

    def clear(self) -> None:
        for key, tog in self.toggles.items():
            tog.set(None)
            self.criteria[key] = None
        self._commit(None, "", "clear_label")
        self.error_var.set("")
        self.error_dirty = False
        self.saved_label.config(text="Currently saved: UNLABELLED")
        self.refresh_verdict()
        self.refresh_progress()

    def go(self, delta: int) -> None:
        new_index = self.index + delta
        if new_index < 0:
            return
        if new_index >= len(self.s.samples):
            self.finish()
            return
        self.index = new_index
        self.load_rep()

    def finish(self) -> None:
        qs = DatasetSample.objects.filter(dataset=self.s.dataset)
        messagebox.showinfo(
            "Annotation complete",
            f"Dataset {self.s.dataset.pk} - {self.s.dataset.name}\n\n"
            f"Total reps:  {len(self.s.samples)}\n"
            f"Labelled:    {qs.filter(is_correct__isnull=False).count()}\n"
            f"Correct:     {qs.filter(is_correct=True).count()}\n"
            f"Incorrect:   {qs.filter(is_correct=False).count()}\n\n"
            f"Audit file: {self.s.audit.path}")
        self.root.destroy()

    def _on_error(self, exc_type, exc, tb) -> None:
        traceback.print_exception(exc_type, exc, tb)
        self.set_status(f"Error: {exc_type.__name__}: {exc}")
        messagebox.showerror("Unexpected error", f"{exc_type.__name__}: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Annotate VectoFit DatasetSample reps.")
    p.add_argument("--dataset", type=int, required=True)
    p.add_argument("--annotator", required=True, help="Django staff/admin username.")
    p.add_argument("--start-rep", type=int, default=None)
    p.add_argument("--audit", type=Path, default=None)
    p.add_argument("--hide-pose", action="store_true")
    p.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None,
                   help="Manual clockwise rotation of raw frames (default: from video metadata).")
    p.add_argument("--landmarks", choices=["raw", "upright"], default="raw",
                   help="Frame the stored landmarks were computed on: 'raw' = unrotated "
                        "(default), 'upright' = already rotated.")
    p.add_argument("--landmark-size", default="1280x720",
                   help="Landmark coordinate space: 'WxH' pixels, 'native' (= raw video "
                        "size) or 'normalized' (0-1).")
    return p.parse_args()


def parse_space(text: str, raw_w: int, raw_h: int) -> tuple:
    t = text.lower()
    if t.startswith("norm"):
        return ("norm", 1, 1)
    if t == "native":
        return ("px", raw_w, raw_h)
    w, h = t.split("x")
    return ("px", int(w), int(h))


def run(args: argparse.Namespace) -> None:
    User = get_user_model()
    dataset = Dataset.objects.select_related("participant").get(pk=args.dataset)
    annotator = User.objects.get(username=args.annotator)
    if not (annotator.is_staff or annotator.is_superuser):
        raise PermissionError(f"User {args.annotator!r} is not a staff/admin user.")

    samples = list(DatasetSample.objects.filter(dataset=dataset)
                   .select_related("rep_assessment").order_by("rep_assessment__rep_number"))
    if not samples:
        raise RuntimeError(f"Dataset {args.dataset} has no DatasetSample records.")
    for s in samples:
        rep = s.rep_assessment
        if rep.start_frame is None or rep.end_frame is None:
            raise RuntimeError(f"Sample {s.pk} / Rep {rep.rep_number} lacks start/end frame.")

    if args.start_rep is not None:
        start_index = next((i for i, s in enumerate(samples)
                            if s.rep_assessment.rep_number >= args.start_rep), 0)
    else:
        start_index = next((i for i, s in enumerate(samples) if s.is_correct is None), 0)

    audit = Audit(args.audit or Path(f"annotation_audit_dataset_{args.dataset}.json"))

    with resolved_video_path(dataset) as video_path:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open dataset video: {video_path}")

        rotation, note = resolve_rotation(cap, args.rotate)
        raw_w, raw_h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_w, out_h = (raw_h, raw_w) if rotation in (90, 270) else (raw_w, raw_h)
        print(f"[video] raw {raw_w}x{raw_h} -> displayed {out_w}x{out_h} "
              f"({'portrait' if out_h > out_w else 'landscape'}) | {note} | cv2 {cv2.__version__}")

        session = Session(
            dataset=dataset, samples=samples, annotator=annotator, cap=cap,
            fps=cap.get(cv2.CAP_PROP_FPS) or 30.0, audit=audit, rotation=rotation,
            lm_space=parse_space(args.landmark_size, raw_w, raw_h), lm_in=args.landmarks,
            start_index=start_index, show_pose=not args.hide_pose)

        try:  # crisp text on Windows high-DPI displays
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        root = tk.Tk()
        global FONT_FAMILY
        installed = set(tkfont.families())
        FONT_FAMILY = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu",
                                        "DejaVu Sans") if f in installed), FONT_FAMILY)
        AnnotatorApp(root, session)
        root.mainloop()
        cap.release()


def main() -> None:
    args = parse_args()
    try:
        run(args)
    except Dataset.DoesNotExist:
        print(f"Dataset {args.dataset} does not exist.", file=sys.stderr)
        raise SystemExit(1)
    except get_user_model().DoesNotExist:
        print(f"Annotator {args.annotator!r} does not exist.", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        traceback.print_exc()
        print(f"\nAnnotation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()