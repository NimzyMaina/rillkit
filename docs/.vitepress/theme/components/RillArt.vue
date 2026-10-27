<script setup lang="ts">
import { computed } from 'vue'
import { makeRills, makeDune, duneRidge } from '../rill'

const props = withDefaults(
  defineProps<{
    uid: string
    seed?: number
    trunks?: number[]
    maxPaths?: number
    bounds?: [number, number]
  }>(),
  { seed: 7, trunks: () => [0.62, 0.8], maxPaths: 64 },
)

const W = 1440
const H = 900
const rills = computed(() =>
  makeRills(props.seed, {
    width: W, height: H, trunks: props.trunks, maxPaths: props.maxPaths, bounds: props.bounds, step: 15,
  }),
)
const dunes = computed(() => [
  { d: makeDune(props.seed + 1, W, H, 770, 34), ridge: duneRidge(props.seed + 1, W, 770, 34), cls: 'far' },
  { d: makeDune(props.seed + 2, W, H, 830, 30), ridge: duneRidge(props.seed + 2, W, 830, 30), cls: 'mid' },
  { d: makeDune(props.seed + 3, W, H, 878, 22), ridge: duneRidge(props.seed + 3, W, 878, 22), cls: 'near' },
])
const id = (s: string) => `${props.uid}-${s}`
</script>

<template>
  <div class="rk-art" aria-hidden="true">
    <div class="rk-layer rk-layer--ground">
      <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient :id="id('soil')" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" class="s-soil0" />
            <stop offset="0.55" class="s-soil1" />
            <stop offset="1" class="s-soil2" />
          </linearGradient>
          <linearGradient :id="id('wa')" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" :y2="H">
            <stop offset="0" class="s-wa0" />
            <stop offset="0.5" class="s-wa1" />
            <stop offset="1" class="s-wa2" />
          </linearGradient>
          <linearGradient :id="id('wb')" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" :y2="H">
            <stop offset="0" class="s-wb0" />
            <stop offset="1" class="s-wb1" />
          </linearGradient>
          <filter :id="id('grain')" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n" />
            <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.9 -0.28" />
          </filter>
          <g :id="id('water')" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path
              v-for="(p, i) in rills" :key="i" :d="p.d" :stroke-width="p.w"
              :stroke="`url(#${id(p.accent ? 'wb' : 'wa')})`"
            />
          </g>
        </defs>
        <rect :width="W" :height="H" :fill="`url(#${id('soil')})`" />
        <rect :width="W" :height="H" class="rk-grain" :filter="`url(#${id('grain')})`" />
        <g class="rk-walls" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path v-for="(p, i) in rills" :key="i" :d="p.d" :stroke-width="p.w + 3.2" />
        </g>
        <use :href="`#${id('water')}`" class="rk-glow" />
        <use :href="`#${id('water')}`" class="rk-water" />
        <g class="rk-trickle" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path
            v-for="(p, i) in rills" :key="i" :d="p.d"
            :stroke-width="Math.max(0.7, p.w * 0.42)"
            :class="{ accent: p.accent }"
            :style="{ animationDuration: p.dur + 's', animationDelay: p.delay + 's' }"
          />
        </g>
      </svg>
    </div>
    <div v-for="(d, i) in dunes" :key="i" class="rk-layer" :class="`rk-layer--${d.cls}`">
      <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMax slice">
        <path :d="d.d" :class="`rk-dune rk-dune--${d.cls}`" />
        <path :d="d.ridge" :class="`rk-ridge rk-ridge--${d.cls}`" fill="none" />
      </svg>
    </div>
  </div>
</template>
