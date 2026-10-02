<script setup lang="ts">
import { onMounted } from "vue";
import { useFeatures } from "../../hooks/useFeatures";
import SummaryCard from "../../components/datasets/SummaryCard.vue";
import FeatureTable from "../../components/features/FeatureTable.vue";
import FeatureGroupGrid from "../../components/features/FeatureGroupGrid.vue";
import PipelineFlow from "../../components/features/PipelineFlow.vue";

const {
  coreFeatures,
  featureGroups,
  pipelineSteps,
  totalFeaturesCount,
  totalGroupsCount,
  fetchFeatures,
} = useFeatures();

onMounted(() => {
  fetchFeatures();
});
</script>

<template>
  <div class="features-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          VECTOFIT FEATURE PIPELINE
        </div>
        <h1>Features</h1>
        <p>
          Define and inspect the biomechanical features extracted from each
          squat repetition.
        </p>
      </div>
    </header>

    <section class="summary-grid">
      <SummaryCard
        label="Total Features"
        :value="totalFeaturesCount"
        description="Core model input features"
        icon="F"
        variant="samples"
      />
      <SummaryCard
        label="Feature Groups"
        :value="totalGroupsCount"
        description="Biomechanical categories"
        icon="G"
        variant="samples"
      />
      <SummaryCard
        label="Sample Unit"
        value="1 Rep"
        description="One completed squat repetition"
        icon="R"
        variant="samples"
      />
      <SummaryCard
        label="Status"
        value="Defined"
        description="Initial feature specification"
        icon="●"
        variant="incorrect"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <h2>Core Features</h2>
          </div>
          <p>Features calculated from pose landmarks and movement data.</p>
        </div>
        <span class="status-badge">{{ totalFeaturesCount }} FEATURES</span>
      </div>
      <FeatureTable :features="coreFeatures" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <h2>Feature Groups</h2>
          </div>
          <p>
            Logical grouping of the biomechanical measurements used by VectoFit.
          </p>
        </div>
      </div>
      <FeatureGroupGrid :groups="featureGroups" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <h2>Feature Extraction Pipeline</h2>
          </div>
          <p>Conceptual flow from pose estimation to model-ready features.</p>
        </div>
      </div>
      <PipelineFlow :steps="pipelineSteps" />
    </section>
  </div>
</template>

<style scoped>
.features-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  font-family: "Segoe UI", Arial, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.page-heading {
  display: flex;
  flex-direction: column;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--vf-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vf-orange);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.page-header h1 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-header p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.section-marker {
  width: 3px;
  height: 17px;
  border-radius: 4px;
  background: var(--vf-gradient);
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 15px;
  font-weight: 700;
}

.section-header p {
  margin: 5px 0 0 12px;
  color: var(--vf-light-muted);
  font-size: 11px;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .features-page {
    padding: 20px;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
