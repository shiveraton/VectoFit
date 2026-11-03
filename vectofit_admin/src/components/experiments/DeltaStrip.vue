<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  full: number;
  ci: [number, number];
  entries: { label: string; value: number; flips: boolean }[];
}>();

const LEFT = 130,
  RIGHT = 600,
  ROW = 28,
  TOP = 16;
const zeroX = (LEFT + RIGHT) / 2;
const span = computed(
  () =>
    Math.max(
      0.05,
      Math.abs(props.full),
      Math.abs(props.ci[0]),
      Math.abs(props.ci[1]),
      ...props.entries.map((e) => Math.abs(e.value)),
    ) * 1.15,
);
const x = (v: number) => zeroX + (v / span.value) * ((RIGHT - LEFT) / 2);
const rows = computed(() => props.entries.length + 1);
const axisY = computed(() => TOP + rows.value * ROW);
const height = computed(() => axisY.value + 34);
const y = (i: number) => TOP + i * ROW + ROW / 2;
const fmt = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(3)}`;
const diamond = (cx: number, cy: number) =>
  `${cx},${cy - 8} ${cx + 8},${cy} ${cx},${cy + 8} ${cx - 8},${cy}`;
</script>

<template>
  <svg
    :viewBox="`0 0 640 ${height}`"
    class="strip"
    role="img"
    aria-label="Change in macro-F1 difference when each participant is removed"
  >
    <line :x1="zeroX" :y1="TOP - 4" :x2="zeroX" :y2="axisY" class="zero" />
    <line :x1="LEFT" :y1="axisY" :x2="RIGHT" :y2="axisY" class="axis" />
    <text :x="LEFT" :y="axisY + 20" class="axis-label">M0 better</text>
    <text :x="zeroX" :y="axisY + 20" text-anchor="middle" class="axis-label">
      0
    </text>
    <text :x="RIGHT" :y="axisY + 20" text-anchor="end" class="axis-label">
      M1 better
    </text>

    <text :x="LEFT - 10" :y="y(0) + 4" text-anchor="end" class="lbl">
      All participants
    </text>
    <line :x1="x(ci[0])" :x2="x(ci[1])" :y1="y(0)" :y2="y(0)" class="ci" />
    <polygon :points="diamond(x(full), y(0))" class="diamond" />
    <text :x="x(ci[1]) + 8" :y="y(0) + 4" class="val">{{ fmt(full) }}</text>

    <g v-for="(e, i) in entries" :key="e.label">
      <text
        :x="LEFT - 10"
        :y="y(i + 1) + 4"
        text-anchor="end"
        class="lbl"
        :class="{ flip: e.flips }"
      >
        Without {{ e.label }}
      </text>
      <circle
        :cx="x(e.value)"
        :cy="y(i + 1)"
        r="6"
        class="dot"
        :class="{ flip: e.flips }"
      />
      <text
        :x="x(e.value) + 12"
        :y="y(i + 1) + 4"
        class="val"
        :class="{ flip: e.flips }"
      >
        {{ fmt(e.value) }}{{ e.flips ? " · sign flip" : "" }}
      </text>
    </g>
  </svg>
</template>

<style scoped>
.strip {
  width: 100%;
  height: auto;
}
.zero {
  stroke: var(--vf-muted, #64748b);
  stroke-dasharray: 3 3;
}
.axis {
  stroke: var(--vf-border-light, rgba(255, 255, 255, 0.15));
}
.axis-label,
.val {
  font-size: 11px;
  fill: var(--vf-light-muted, #94a3b8);
}
.lbl {
  font-size: 12px;
  fill: var(--vf-dark, #f8fafc);
}
.ci {
  stroke: var(--vf-orange, #f97316);
  stroke-width: 3;
  opacity: 0.5;
  stroke-linecap: round;
}
.diamond {
  fill: var(--vf-orange, #f97316);
}
.dot {
  fill: var(--vf-light-muted, #94a3b8);
}
.dot.flip,
.lbl.flip,
.val.flip {
  fill: #f87171;
}
</style>
