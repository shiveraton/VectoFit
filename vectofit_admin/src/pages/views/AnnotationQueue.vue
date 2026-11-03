<template>
  <section class="queue-page">
    <header>
      <div>
        <h1>Annotation queue</h1>
        <p>Choose a dataset to review.</p>
      </div>
      <button @click="load">Refresh</button>
    </header>
    <p v-if="isLoading">Loading datasets…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <div v-else-if="datasets.length" class="queue-list">
      <article v-for="dataset in datasets" :key="dataset.id" class="queue-card">
        <div>
          <h2>{{ dataset.name }}</h2>
          <p>{{ dataset.exercise_type.replaceAll("_", " ") }}</p>
        </div>
        <div class="progress">
          <strong
            >{{ dataset.annotated_by_me }} / {{ dataset.review_total }}</strong
          ><progress
            :value="dataset.annotated_by_me"
            :max="Math.max(dataset.review_total, 1)"
          /><span>{{ dataset.pending_for_me }} remaining</span>
        </div>
        <RouterLink :to="`/dataset/${dataset.id}/annotate`"
          >Open annotation</RouterLink
        >
      </article>
    </div>
    <p v-else>No datasets are available for annotation.</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useAnnotationQueue } from "../../hooks/useAnnotationQueue";
const { datasets, isLoading, error, load } = useAnnotationQueue();
onMounted(load);
</script>

<style scoped>
.queue-page {
  color: var(--text-primary, #25201e);
}
header,
.queue-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
header {
  margin-bottom: 1.5rem;
}
h1,
h2,
p {
  margin: 0;
}
header p,
.queue-card p {
  color: var(--text-muted, #766d69);
  margin-top: 0.35rem;
}
.queue-list {
  display: grid;
  gap: 0.8rem;
}
.queue-card {
  background: var(--surface, white);
  border: 1px solid var(--border, #eee6e2);
  border-radius: 12px;
  padding: 1.2rem;
}
.progress {
  display: grid;
  gap: 0.2rem;
}
.progress span {
  color: var(--text-muted, #766d69);
  font-size: 0.85rem;
}
a,
button {
  color: var(--accent, #e94b23);
}
</style>
