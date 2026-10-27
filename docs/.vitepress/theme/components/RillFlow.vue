<script setup lang="ts">
interface Node { id: string; x: number; y: number; w: number; label: string; sub: string; kind?: 'ok' | 'retry' | 'dlq' }
interface Edge { d: string; kind?: 'ok' | 'retry' | 'dlq'; arrow?: boolean }

const H = {
  box: '0 0 1100 460',
  nodes: [
    { id: 'pub', x: 90, y: 220, w: 128, label: 'Publish', sub: 'broker.publish()' },
    { id: 'stream', x: 320, y: 220, w: 128, label: 'Stream', sub: 'XADD orders' },
    { id: 'group', x: 550, y: 220, w: 128, label: 'Group', sub: 'workers' },
    { id: 'handler', x: 780, y: 220, w: 128, label: 'Handler', sub: 'your function' },
    { id: 'ack', x: 1010, y: 70, w: 110, label: 'Ack', sub: 'XACK, done', kind: 'ok' },
    { id: 'dlq', x: 1010, y: 220, w: 110, label: 'DLQ', sub: 'orders-dlq', kind: 'dlq' },
    { id: 'retry', x: 1010, y: 370, w: 110, label: 'Retry', sub: 'after backoff', kind: 'retry' },
  ] as Node[],
  edges: [
    { d: 'M156 220 C 192 190 208 252 254 220', arrow: true },
    { d: 'M386 220 C 424 252 450 190 484 220', arrow: true },
    { d: 'M616 220 C 652 190 680 252 714 220', arrow: true },
    { d: 'M846 212 C 896 176 904 70 950 70', kind: 'ok', arrow: true },
    { d: 'M846 220 C 884 236 912 204 950 220', kind: 'dlq', arrow: true },
    { d: 'M846 228 C 896 266 904 370 950 370', kind: 'retry', arrow: true },
    { d: 'M1010 398 C 1010 442 900 436 780 434 C 660 432 556 440 550 252', kind: 'retry', arrow: true },
  ] as Edge[],
  loop: { d: 'M1010 398 C 1010 442 900 436 780 434 C 660 432 556 440 550 252', text: 'redelivered after backoff', x: 520, y: 420 },
}

const V = {
  box: '0 0 360 690',
  nodes: [
    { id: 'pub', x: 180, y: 40, w: 150, label: 'Publish', sub: 'broker.publish()' },
    { id: 'stream', x: 180, y: 160, w: 150, label: 'Stream', sub: 'XADD orders' },
    { id: 'group', x: 180, y: 280, w: 150, label: 'Group', sub: 'workers' },
    { id: 'handler', x: 180, y: 400, w: 150, label: 'Handler', sub: 'your function' },
    { id: 'ack', x: 62, y: 600, w: 96, label: 'Ack', sub: 'XACK', kind: 'ok' },
    { id: 'dlq', x: 180, y: 600, w: 96, label: 'DLQ', sub: 'orders-dlq', kind: 'dlq' },
    { id: 'retry', x: 298, y: 600, w: 96, label: 'Retry', sub: 'backoff', kind: 'retry' },
  ] as Node[],
  edges: [
    { d: 'M180 68 C 150 92 214 110 180 130', arrow: true },
    { d: 'M180 188 C 214 212 150 230 180 250', arrow: true },
    { d: 'M180 308 C 150 332 214 350 180 370', arrow: true },
    { d: 'M150 428 C 120 480 62 500 62 572', kind: 'ok', arrow: true },
    { d: 'M180 428 C 160 480 200 520 180 572', kind: 'dlq', arrow: true },
    { d: 'M210 428 C 240 480 298 500 298 572', kind: 'retry', arrow: true },
    { d: 'M298 628 C 330 700 358 640 350 520 C 344 400 330 330 258 292', kind: 'retry', arrow: true },
  ] as Edge[],
  loop: { d: 'M298 628 C 330 700 358 640 350 520 C 344 400 330 330 258 292', text: '', x: 0, y: 0 },
}

const layouts = [
  { cls: 'rk-flow__svg--h', ...H },
  { cls: 'rk-flow__svg--v', ...V },
]
const steps = [
  { k: 'ok', t: 'Handler returns', d: 'The entry is acked and leaves the pending list.' },
  { k: 'retry', t: 'Handler raises', d: 'It is nacked and delivered again after a growing backoff.' },
  { k: 'dlq', t: 'Retries run out', d: 'It moves to the DLQ with the error, original id and delivery count.' },
]
</script>

<template>
  <section class="rk-section rk-flowsec" aria-labelledby="rk-flow-h">
    <div class="rk-wrap">
      <header class="rk-head">
        <p class="rk-kicker">How it flows</p>
        <h2 id="rk-flow-h" class="rk-h2">Every message ends up <em>somewhere</em>.</h2>
        <p class="rk-sub">Downhill from publish to handler, then one of three outcomes. None of them is "lost".</p>
      </header>
      <div class="rk-flow">
        <svg
          v-for="(l, li) in layouts" :key="li" :viewBox="l.box" :class="['rk-flow__svg', l.cls]"
          role="img"
          aria-label="Diagram: publish to stream to consumer group to handler, which ends in ack, retry after backoff, or the dead-letter queue."
        >
          <defs>
            <marker v-for="k in ['ok', 'retry', 'dlq', 'base']" :id="`ah-${li}-${k}`" :key="k" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M1 1 L8 5 L1 9 Z" :class="`ah ah--${k}`" />
            </marker>
            <linearGradient :id="`fg-${li}`" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" class="s-wa0" /><stop offset="1" class="s-wa1" />
            </linearGradient>
          </defs>
          <g fill="none" stroke-linecap="round">
            <template v-for="(e, i) in l.edges" :key="i">
              <path :d="e.d" class="rk-edge-wall" />
              <path :d="e.d" :class="['rk-edge', `rk-edge--${e.kind || 'base'}`]" :marker-end="`url(#ah-${li}-${e.kind || 'base'})`" />
              <path :d="e.d" :class="['rk-edge-flow', `rk-edge-flow--${e.kind || 'base'}`]" :style="{ animationDuration: 2.4 + (i % 3) * 0.7 + 's' }" />
            </template>
          </g>
          <g v-for="n in l.nodes" :key="n.id" :class="['rk-node', n.kind && `rk-node--${n.kind}`]" :transform="`translate(${n.x} ${n.y})`">
            <rect :x="-n.w / 2" :y="l.cls.endsWith('h') ? -27 : -31" :width="n.w" :height="l.cls.endsWith('h') ? 54 : 62" :rx="l.cls.endsWith('h') ? 27 : 31" />
            <text :y="l.cls.endsWith('h') ? 6 : -3" text-anchor="middle" class="rk-node__t">{{ n.label }}</text>
            <text :y="l.cls.endsWith('h') ? -40 : 17" text-anchor="middle" :class="['rk-node__s', l.cls.endsWith('v') && 'is-in']">{{ n.sub }}</text>
          </g>
          <text v-if="l.loop.text" :x="l.loop.x" :y="l.loop.y" text-anchor="middle" class="rk-loop-label">{{ l.loop.text }}</text>
        </svg>
      </div>
      <ul class="rk-outcomes">
        <li v-for="s in steps" :key="s.k" :class="`rk-out--${s.k}`">
          <b>{{ s.t }}</b>
          <span>{{ s.d }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
