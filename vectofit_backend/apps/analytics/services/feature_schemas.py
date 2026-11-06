from dataclasses import dataclass

from . import features, fppa


@dataclass(frozen=True)
class FeatureSchema:
    version: str
    feature_order: tuple[str, ...]
    prediction_target: str
    trainable: bool


SCHEMAS = {
    features.FEATURE_SCHEMA_VERSION: FeatureSchema(
        version=features.FEATURE_SCHEMA_VERSION,
        feature_order=tuple(features.FEATURE_ORDER),
        prediction_target="binary_form",
        trainable=False,
    ),
    fppa.FEATURE_SCHEMA_VERSION: FeatureSchema(
        version=fppa.FEATURE_SCHEMA_VERSION,
        feature_order=tuple(fppa.M1_FEATURES),
        prediction_target="knee_alignment",
        trainable=True,
    ),
}

CURRENT = {"knee_alignment": fppa.FEATURE_SCHEMA_VERSION}
LEGACY_TARGET_SCHEMAS = {
    "binary_form": features.FEATURE_SCHEMA_VERSION,
    "error_type": features.FEATURE_SCHEMA_VERSION,
}


def schema_for_target(prediction_target: str) -> FeatureSchema:
    prediction_target = getattr(prediction_target, "value", prediction_target)
    try:
        version = CURRENT.get(prediction_target)
        if version is None:
            version = LEGACY_TARGET_SCHEMAS[prediction_target]
        return SCHEMAS[version]
    except KeyError as exc:
        raise ValueError(
            f"No trainable feature schema is registered for {prediction_target!r}."
        ) from exc


def schema_for_version(version: str) -> FeatureSchema | None:
    return SCHEMAS.get(version)
