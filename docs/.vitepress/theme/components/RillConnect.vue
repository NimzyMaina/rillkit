<script setup lang="ts">
// Two editor windows joined by a rill. Geometry is fixed (tab bar + padding + line height)
// so the channel can start at the publish() line and end at the handler's def line.
const TAB = 38
const PAD = 16
const LH = 24
const LINES_A = 5
const LINES_B = 17
const PUB_LINE = 5 // 1-based line in publish.py
const SUB_LINE = 10 // 1-based line in worker.py (the "def handle" line)

const H = TAB + PAD * 2 + Math.max(LINES_A, LINES_B) * LH
const y0 = TAB + PAD + (PUB_LINE - 0.5) * LH
const y1 = TAB + PAD + (SUB_LINE - 0.5) * LH
const W = 120
const dH = `M0 ${y0} C ${W * 0.55} ${y0}, ${W * 0.45} ${y1}, ${W} ${y1}`
// mobile: panels stacked, channel runs down the left gutter between them
const dV = 'M28 0 C 28 34, 62 40, 62 80 S 28 126, 28 160'
</script>

<template>
  <section class="rk-connect-sec" aria-labelledby="rk-connect-h">
  <div class="rk-wrap">
  <header class="rk-connect__head">
    <h2 id="rk-connect-h" class="rk-h2">Two files and a stream name</h2>
    <p class="rk-sub">
      The publisher and the worker agree on <code>"orders"</code> and nothing else. No schema to register, no polling
      loop, no ack bookkeeping. The path below is the one message 42.5 takes.
    </p>
  </header>
  <div class="rk-connect" :style="{ '--tab': TAB + 'px', '--pad': PAD + 'px', '--lh': LH + 'px', '--h': H + 'px' }">
    <figure class="rk-win vp-doc rk-win--pub">
      <slot name="publish" />
    </figure>

    <svg class="rk-wire rk-wire--h" :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H" aria-hidden="true">
      <path :d="dH" class="rk-wire__bed" />
      <path :d="dH" class="rk-wire__flow" pathLength="100" />
      <circle r="5" class="rk-wire__token">
        <animateMotion :path="dH" dur="4.8s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;0.7;1" calcMode="linear" />
      </circle>
      <circle cx="0" :cy="y0" r="4" class="rk-wire__end" />
      <circle :cx="W" :cy="y1" r="4" class="rk-wire__end" />
    </svg>
    <svg class="rk-wire rk-wire--v" viewBox="0 0 90 160" width="90" height="160" aria-hidden="true">
      <path :d="dV" class="rk-wire__bed" />
      <path :d="dV" class="rk-wire__flow" pathLength="100" />
      <circle r="5" class="rk-wire__token">
        <animateMotion :path="dV" dur="3.6s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;0.7;1" calcMode="linear" />
      </circle>
    </svg>

    <figure class="rk-win vp-doc rk-win--sub">
      <slot name="consume" />
    </figure>
  </div>
  </div>
  </section>
</template>
