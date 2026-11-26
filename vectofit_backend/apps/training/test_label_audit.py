from django.test import SimpleTestCase

from .services.label_audit import score_label_audit, select_audit_samples


class LabelAuditTests(SimpleTestCase):
    def test_selection_is_reproducible_and_spreads_participants(self):
        rows = [
            {"source": source, "participant_id": participant, "sample_id": f"{source}-{participant}-{rep}"}
            for source in ("mdy", "zen") for participant in range(4) for rep in range(3)
        ]
        selected = select_audit_samples(rows, per_source=4)
        self.assertEqual(selected, select_audit_samples(rows, per_source=4))
        self.assertEqual(len({r["sample_id"] for r in selected}), 8)
        for source in ("mdy", "zen"):
            self.assertEqual(len({r["participant_id"] for r in selected if r["source"] == source}), 4)

    def test_kappa_compares_each_review_with_frozen_labels_and_other_review(self):
        manifest = {"samples": [
            {"audit_id": "R001", "target": "good", "source": "mdy"},
            {"audit_id": "R002", "target": "bad", "source": "mdy"},
        ]}
        def review(grades):
            return {"samples": [
                {"audit_id": f"R{i:03d}", "annotation": {"notes": "", **{
                    side: {"grade": grade, "direction": "none" if grade == "aligned" else "valgus"}
                    for side in ("left", "right")
                }}} for i, grade in enumerate(grades, 1)
            ]}
        a = review(["aligned", "deviated"])
        b = review(["deviated", "aligned"])
        result = score_label_audit(manifest, {"A": a, "B": b})["all"]
        self.assertEqual(result["current_vs_A"]["kappa"], 1)
        self.assertEqual(result["current_vs_B"]["kappa"], -1)
        self.assertEqual(result["A_vs_B"]["kappa"], -1)
        b["samples"].pop()
        with self.assertRaises(ValueError):
            score_label_audit(manifest, {"A": a, "B": b})

    def test_blank_review_is_rejected(self):
        manifest = {"samples": [{"audit_id": "R001", "target": "good", "source": "mdy"}]}
        review = {"samples": [{"audit_id": "R001", "annotation": {"notes": "", **{
            side: {"grade": None, "direction": None} for side in ("left", "right")
        }}}]}
        with self.assertRaises(ValueError):
            score_label_audit(manifest, {"A": review, "B": review})
