<script setup lang="ts">
</script>

<template>
  <section class="configuration-section wide-section">
    <div class="configuration-label">
      <div>
        <strong>View Angle</strong>
        <span>FPPA measures bilateral knee alignment from a front-facing camera view.</span>
      </div>
    </div>

    <div class="view-options">
      <div class="view-option selected" aria-current="true">
        <span class="view-icon" aria-hidden="true">F</span>
        <span class="view-copy">
          <strong>Frontal</strong>
          <small>Required FPPA view</small>
          <span>Training and assessment use the same frontal-plane measurement schema.</span>
        </span>
        <span class="view-indicator" aria-hidden="true"></span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.configuration-section {
  padding: 24px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.wide-section {
  grid-column: 1 / -1;
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

.view-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.view-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  padding: 13px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 9px;
  cursor: default;
}

.view-option.selected {
  background: #fffaf6;
  border-color: #fb923c;
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.08);
}

.view-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-radius: 7px;
  font-size: 11px;
  font-weight: 800;
}

.view-copy {
  min-width: 0;
  flex: 1;
}

.view-copy strong,
.view-copy small,
.view-copy > span {
  display: block;
}

.view-copy strong {
  color: var(--vf-text);
  font-size: 13px;
  font-weight: 700;
}

.view-copy small {
  margin-top: 2px;
  color: var(--vf-orange-dark);
  font-size: 11px;
  font-weight: 700;
}

.view-copy > span {
  margin-top: 6px;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.45;
}

.view-indicator {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  margin-top: 2px;
  border: 1.5px solid #d4d4d8;
  border-radius: 50%;
}

.selected .view-indicator {
  border: 3px solid #fb923c;
  box-shadow: inset 0 0 0 1px #ffffff;
}

@media (max-width: 800px) {
  .view-options {
    grid-template-columns: 1fr;
  }
}
</style>
