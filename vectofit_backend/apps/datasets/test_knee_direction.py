from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from .serializers import KneeAnnotationField


class KneeDirectionTests(SimpleTestCase):
    def annotation(self, grade, direction):
        return {"left": {"grade": grade, "direction": direction},
                "right": {"grade": "aligned", "direction": "none"}, "notes": ""}

    def test_deviated_requires_explicit_valgus_or_varus(self):
        field = KneeAnnotationField()
        for direction in ("valgus", "varus"):
            self.assertEqual(field.to_internal_value(self.annotation("deviated", direction))["left"]["direction"], direction)
        for direction in ("uncertain", "none", None, ""):
            with self.subTest(direction=direction), self.assertRaises(ValidationError):
                field.to_internal_value(self.annotation("deviated", direction))

    def test_aligned_has_no_deviation_direction(self):
        field = KneeAnnotationField()
        self.assertEqual(field.to_internal_value(self.annotation("aligned", "none"))["left"]["direction"], "none")
        for direction in ("valgus", "varus", "uncertain", None):
            with self.subTest(direction=direction), self.assertRaises(ValidationError):
                field.to_internal_value(self.annotation("aligned", direction))
