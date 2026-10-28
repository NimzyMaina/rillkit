<script setup lang="ts">
import { makeDivider } from '../rill'

const props = withDefaults(defineProps<{ seed?: number; tone?: number }>(), { seed: 3, tone: 0 })
const d = makeDivider(props.seed)
</script>

<template>
  <div class="rk-divider" aria-hidden="true">
    <svg :viewBox="`0 0 ${d.width} ${d.height}`" preserveAspectRatio="none">
      <g fill="none" stroke-linecap="round" stroke-linejoin="round" :class="`t${tone}`">
        <path :d="d.d" class="rk-divider__line" />
        <path :d="d.branch" class="rk-divider__line rk-divider__line--b" />
        <path :d="d.d" pathLength="100" class="rk-divider__flow" />
      </g>
    </svg>
  </div>
</template>
