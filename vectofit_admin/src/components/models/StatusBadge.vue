<script setup lang="ts">
import type { DeploymentStatus } from "../../services/modelService";

defineProps<{
  status: DeploymentStatus;
  environment?: string;
}>();
</script>

<template>
  <div
    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
    :class="{
      'bg-emerald-500/10 text-emerald-400 border-emerald-500/20':
        status === 'active',
      'bg-amber-500/10 text-amber-400 border-amber-500/20':
        status === 'building',
      'bg-rose-500/10 text-rose-400 border-rose-500/20': status === 'failed',
      'bg-slate-500/10 text-slate-400 border-slate-500/20':
        status === 'inactive',
    }"
  >
    <span
      class="h-1.5 w-1.5 rounded-full"
      :class="{
        'bg-emerald-400 animate-pulse': status === 'active',
        'bg-amber-400 animate-spin': status === 'building',
        'bg-rose-400': status === 'failed',
        'bg-slate-400': status === 'inactive',
      }"
    />
    <span class="capitalize">{{ status }}</span>
    <span v-if="environment" class="text-slate-500 font-normal"
      >({{ environment }})</span
    >
  </div>
</template>
