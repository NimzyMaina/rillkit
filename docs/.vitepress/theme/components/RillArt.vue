<script setup lang="ts">
import { computed } from 'vue'
import { makeRills } from '../rill'

const props = withDefaults(
  defineProps<{
    seed?: number
    trunks?: number[]
    maxPaths?: number
    bounds?: [number, number]
    height?: number
  }>(),
  { seed: 7, trunks: () => [0.62, 0.8], maxPaths: 14, height: 900 },
)

const W = 1440
const rills = computed(() =>
  makeRills(props.seed, {
    width: W, height: props.height, trunks: props.trunks, maxPaths: props.maxPaths, bounds: props.bounds, step: 16,
  }),
)
</script>

<template>
  <div class="rk-art" aria-hidden="true">
    <svg :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="xMidYMax slice">
      <g class="rk-rills" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path v-for="(p, i) in rills" :key="i" :d="p.d" :stroke-width="p.w" :class="`t${p.tone}`" />
      </g>
      <g class="rk-rills-flow" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path
          v-for="(p, i) in rills" :key="i" :d="p.d" :stroke-width="p.w + 0.6" pathLength="100" :class="`t${p.tone}`"
          :style="{ animationDuration: p.dur + 's', animationDelay: p.delay + 's' }"
        />
      </g>
    </svg>
  </div>
</template>
