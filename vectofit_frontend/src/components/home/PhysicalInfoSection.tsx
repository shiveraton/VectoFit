import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";

import type { PhysicalInformationPayload } from "../../features/profile/services/profileService";
import usePhysicalInformation from "../../features/profile/hooks/usePhysicalInformation";
import styles, { COLORS } from "../../styles/HomeScreenStyles";

function calculateBMI(
  weightKg: number | null,
  heightCm: number | null,
): number | null {
  if (weightKg == null || heightCm == null || weightKg <= 0 || heightCm <= 0) {
    return null;
  }

  const heightM = heightCm / 100;
  return Number((weightKg / (heightM * heightM)).toFixed(1));
}

export default function PhysicalInfoSection() {
  const { weight, height, isLoading, savePhysicalInformation } =
    usePhysicalInformation();

  const [editorVisible, setEditorVisible] = useState(false);
  const [weightInput, setWeightInput] = useState("");
  const [heightInput, setHeightInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const bmi = calculateBMI(weight, height);

  const openEditor = () => {
    setWeightInput(weight == null ? "" : String(weight));
    setHeightInput(height == null ? "" : String(height));
    setFormError("");
    setEditorVisible(true);
  };

  const handleSave = async () => {
    const parseOptionalNumber = (value: string): number | null => {
      const trimmed = value.trim();

      if (!trimmed) {
        return null;
      }

      const parsed = Number(trimmed.replace(",", "."));
      return Number.isFinite(parsed) ? parsed : Number.NaN;
    };

    const nextWeight = parseOptionalNumber(weightInput);
    const nextHeight = parseOptionalNumber(heightInput);

    if (
      nextWeight !== null &&
      (!Number.isFinite(nextWeight) || nextWeight < 20 || nextWeight > 500)
    ) {
      setFormError("Enter a valid weight between 20 and 500 kg.");
      return;
    }

    if (
      nextHeight !== null &&
      (!Number.isFinite(nextHeight) || nextHeight < 50 || nextHeight > 250)
    ) {
      setFormError("Enter a valid height between 50 and 250 cm.");
      return;
    }

    const payload: PhysicalInformationPayload = {
      weight_kg: nextWeight,
      height_cm: nextHeight,
    };

    try {
      setSaving(true);
      setFormError("");

      await savePhysicalInformation(payload);
      setEditorVisible(false);
    } catch (error) {
      console.error("Failed to save physical information:", error);
      setFormError(
        "Unable to save your information. Check your connection and try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Pressable
        style={styles.card}
        onPress={openEditor}
        accessibilityRole="button"
        accessibilityLabel="Edit physical information"
        accessibilityHint="Opens the weight and height editor"
      >
        <View style={styles.cardHeaderRow}>
          <Text style={styles.cardTitle}>Physical Information</Text>

          <View style={[styles.statusChip, styles.statusChipUncalibrated]}>
            <View style={[styles.statusDot, styles.statusDotUncalibrated]} />
            <Text style={[styles.statusText, styles.statusTextUncalibrated]}>
              Not Calibrated
            </Text>
          </View>
        </View>

        <View style={styles.inputsGrid}>
          <View style={styles.inputCol}>
            <Text style={styles.inputLabel}>Weight</Text>
            <View style={styles.textInput}>
              <Text style={styles.infoText}>
                {isLoading
                  ? "Loading..."
                  : weight == null
                    ? "Add weight"
                    : `${weight} kg`}
              </Text>
            </View>
          </View>

          <View style={styles.inputCol}>
            <Text style={styles.inputLabel}>Height</Text>
            <View style={styles.textInput}>
              <Text style={styles.infoText}>
                {isLoading
                  ? "Loading..."
                  : height == null
                    ? "Add height"
                    : `${height} cm`}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.bmiDisplayCard}>
          <View style={styles.bmiLabelGroup}>
            <Text style={styles.bmiLabel}>BMI</Text>
            <Text style={styles.bmiSubtext}>Body Mass Index</Text>
          </View>

          <Text style={styles.bmiValue}>
            {bmi == null ? "--" : bmi.toFixed(1)}
          </Text>
        </View>

        <Text style={styles.editHint}>Tap anywhere on this card to edit</Text>
      </Pressable>

      <Modal
        visible={editorVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setEditorVisible(false)}
      >
        <View style={styles.modalBackdrop}>
          <KeyboardAvoidingView
            style={styles.modalKeyboardContainer}
            behavior={Platform.OS === "ios" ? "padding" : "height"}
          >
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>Physical Information</Text>

              <Text style={styles.modalSubtitle}>
                Enter your measurements to calculate BMI.
              </Text>

              <Text style={styles.inputLabel}>Weight (kg)</Text>
              <TextInput
                style={[styles.textInput, styles.modalInput]}
                value={weightInput}
                onChangeText={setWeightInput}
                keyboardType="decimal-pad"
                placeholder="e.g. 75.5"
                placeholderTextColor={COLORS.textMuted}
                maxLength={6}
                editable={!saving}
              />

              <Text style={styles.inputLabel}>Height (cm)</Text>
              <TextInput
                style={[styles.textInput, styles.modalInput]}
                value={heightInput}
                onChangeText={setHeightInput}
                keyboardType="decimal-pad"
                placeholder="e.g. 170"
                placeholderTextColor={COLORS.textMuted}
                maxLength={6}
                editable={!saving}
              />

              {formError ? (
                <Text style={styles.modalError}>{formError}</Text>
              ) : null}

              <View style={styles.modalActions}>
                <Pressable
                  style={[styles.modalButton, styles.modalSecondaryButton]}
                  disabled={saving}
                  onPress={() => setEditorVisible(false)}
                >
                  <Text style={styles.modalSecondaryButtonText}>Cancel</Text>
                </Pressable>

                <Pressable
                  style={[styles.modalButton, styles.modalPrimaryButton]}
                  disabled={saving}
                  onPress={handleSave}
                >
                  {saving ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.modalButtonText}>Save changes</Text>
                  )}
                </Pressable>
              </View>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </>
  );
}
