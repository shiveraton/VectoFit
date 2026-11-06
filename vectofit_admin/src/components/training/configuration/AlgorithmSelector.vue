<script setup lang="ts">
</script>

<template>
  <section class="configuration-section">
    <div class="configuration-label">
      <div>
        <strong>Current Model</strong>
        <span>The FPPA M1 experiment uses a fixed XGBoost classifier.</span>
      </div>
    </div>

    <div class="algorithm-card selected">
      <span class="algorithm-icon">XGB</span>
      <span class="algorithm-copy">
        <strong>XGBoost · FPPA M1</strong>
        <span>Predicts human-reviewed good/bad knee-alignment labels from the fixed FPPA v2 feature schema.</span>
      </span>
    </div>
    <p class="algorithm-note">
      M0 uses four FPPA features; M1 adds bilateral asymmetry. Both are
      XGBoost models. The fixed 10-degree threshold rule is evaluated separately
      on the M0 / M1 Results page.
    </p>
  </section>
</template>

<style scoped>
.configuration-section {
  min-width: 0;
  padding: 24px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.configuration-label {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 15px;
}

.configuration-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 27px;
  height: 27px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 800;
}

.configuration-label strong,
.configuration-label span {
  display: block;
}

.configuration-label strong {
  color: var(--vf-text);
  font-size: 12px;
}

.configuration-label div > span {
  margin-top: 4px;
  color: var(--vf-light-muted);
  font-size: 12px;
}

.algorithm-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.algorithm-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  cursor: default;
}

.algorithm-card.selected {
  background: var(--vf-orange-soft);
  border-color: #fb923c;
}

.algorithm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  color: #ffffff;
  background: var(--vf-gradient);
  border-radius: 8px;
  font-size: 11px;
  font-weight: 800;
}

.algorithm-copy {
  min-width: 0;
  flex: 1;
}

.algorithm-copy strong,
.algorithm-copy span {
  display: block;
}

.algorithm-copy strong {
  color: var(--vf-text);
  font-size: 12px;
}

.algorithm-copy span {
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.45;
}

.algorithm-status {
  flex-shrink: 0;
  color: var(--vf-light-muted);
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
}

.selected .algorithm-status {
  color: var(--vf-orange-dark);
}

.algorithm-note,
.inline-empty {
  margin-top: 10px;
  color: var(--vf-light-muted);
  background: #fcfcfc;
  border: 1px dashed var(--vf-border);
  border-radius: 7px;
  font-size: 11px;
  line-height: 1.5;
}

.algorithm-note {
  padding: 9px 10px;
}

.inline-empty {
  padding: 15px;
  text-align: center;
}
</style>
