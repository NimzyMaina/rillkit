<script setup lang="ts">
type Kind = 'ok' | 'retry' | 'dlq'
interface Node { id: string; x: number; y: number; w: number; label: string; sub: string; kind?: Kind }
interface Edge { d: string; kind?: Kind }

const H = {
  box: '0 36 1100 396',
  nodes: [
    { id: 'pub', x: 90, y: 210, w: 132, label: 'Publish', sub: 'broker.publish()' },
    { id: 'stream', x: 320, y: 210, w: 132, label: 'Stream', sub: 'orders' },
    { id: 'group', x: 550, y: 210, w: 132, label: 'Group', sub: 'workers' },
    { id: 'handler', x: 780, y: 210, w: 132, label: 'Handler', sub: 'your function' },
    { id: 'ack', x: 1010, y: 70, w: 110, label: 'Ack', sub: 'done', kind: 'ok' },
    { id: 'dlq', x: 1010, y: 210, w: 110, label: 'DLQ', sub: 'orders-dlq', kind: 'dlq' },
    { id: 'retry', x: 1010, y: 350, w: 110, label: 'Retry', sub: 'after backoff', kind: 'retry' },
  ] as Node[],
  edges: [
    { d: 'M158 210 H250' },
    { d: 'M388 210 H480' },
    { d: 'M618 210 H710' },
    { d: 'M848 200 C 902 200 902 70 950 70', kind: 'ok' },
    { d: 'M848 210 H950', kind: 'dlq' },
    { d: 'M848 220 C 902 220 902 350 950 350', kind: 'retry' },
    { d: 'M1010 380 V398 Q1010 420 988 420 H572 Q550 420 550 398 V244', kind: 'retry' },
  ] as Edge[],
  loop: { text: 'redelivered after backoff', x: 780, y: 410 },
  bracket: { x: 468, y: 168, w: 396, h: 84 },
}

const V = {
  box: '0 0 360 690',
  nodes: [
    { id: 'pub', x: 180, y: 40, w: 150, label: 'Publish', sub: 'broker.publish()' },
    { id: 'stream', x: 180, y: 160, w: 150, label: 'Stream', sub: 'orders' },
    { id: 'group', x: 180, y: 280, w: 150, label: 'Group', sub: 'workers' },
    { id: 'handler', x: 180, y: 400, w: 150, label: 'Handler', sub: 'your function' },
    { id: 'ack', x: 62, y: 590, w: 96, label: 'Ack', sub: 'done', kind: 'ok' },
    { id: 'dlq', x: 180, y: 590, w: 96, label: 'DLQ', sub: 'orders-dlq', kind: 'dlq' },
    { id: 'retry', x: 298, y: 590, w: 96, label: 'Retry', sub: 'backoff', kind: 'retry' },
  ] as Node[],
  edges: [
    { d: 'M180 72 V126' },
    { d: 'M180 192 V246' },
    { d: 'M180 312 V366' },
    { d: 'M150 432 C 150 500 62 490 62 556', kind: 'ok' },
    { d: 'M180 432 V556', kind: 'dlq' },
    { d: 'M210 432 C 210 500 298 490 298 556', kind: 'retry' },
    { d: 'M298 622 V640 Q298 654 312 654 H328 Q342 654 342 640 V294 Q342 280 328 280 H258', kind: 'retry' },
  ] as Edge[],
  loop: { text: '', x: 0, y: 0 },
  bracket: null as null | { x: number; y: number; w: number; h: number },
}

const layouts = [
  { cls: 'rk-flow__svg--h', ...H },
  { cls: 'rk-flow__svg--v', ...V },
]
const steps = [
  { k: 'ok', t: 'Ack', d: 'The handler returned. The entry is acked and leaves the pending list.' },
  { k: 'retry', t: 'Retry', d: 'The handler raised, or called nack(). It is delivered again after a growing backoff, up to max_retries.' },
  { k: 'dlq', t: 'Dead letter', d: 'Retries ran out, or you called reject(). The entry moves to the DLQ with the error, original id and delivery count.' },
]
</script>

<template>
  <section class="rk-section rk-flowsec" aria-labelledby="rk-flow-h">
    <div class="rk-wrap">
      <header class="rk-head">
        <h2 id="rk-flow-h" class="rk-h2">Where a message ends up</h2>
        <p class="rk-sub">It goes from publish to the handler, then takes one of three exits. There is no fourth one where it quietly disappears.</p>
      </header>
      <div class="rk-flow">
        <svg
          v-for="(l, li) in layouts" :key="li" :viewBox="l.box" :class="['rk-flow__svg', l.cls]"
          role="img"
          aria-label="Diagram: publish to stream to consumer group to handler, which ends in ack, retry after backoff, or the dead-letter queue."
        >
          <defs>
            <marker v-for="k in ['ok', 'retry', 'dlq', 'base']" :id="`ah-${li}-${k}`" :key="k" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M1 1.5 L8 5 L1 8.5" fill="none" :class="`ah ah--${k}`" />
            </marker>
          </defs>
          <g v-if="l.bracket" class="rk-bracket">
            <rect :x="l.bracket.x" :y="l.bracket.y" :width="l.bracket.w" :height="l.bracket.h" rx="10" />
            <text :x="l.bracket.x + 12" :y="l.bracket.y - 8" class="rk-bracket__t">middleware wraps this part</text>
          </g>
          <g fill="none" stroke-linecap="round" stroke-linejoin="round">
            <template v-for="(e, i) in l.edges" :key="i">
              <path :d="e.d" :class="['rk-edge', `rk-edge--${e.kind || 'base'}`]" :marker-end="`url(#ah-${li}-${e.kind || 'base'})`" />
              <path :d="e.d" pathLength="100" :class="['rk-edge-flow', `rk-edge-flow--${e.kind || 'base'}`]" :style="{ animationDuration: 14 + (i % 3) * 4 + 's', animationDelay: -i * 3 + 's' }" />
            </template>
          </g>
          <g v-for="n in l.nodes" :key="n.id" :class="['rk-node', n.kind && `rk-node--${n.kind}`]" :transform="`translate(${n.x} ${n.y})`">
            <rect :x="-n.w / 2" y="-28" :width="n.w" height="56" rx="7" />
            <text y="-3" text-anchor="middle" class="rk-node__t">{{ n.label }}</text>
            <text y="15" text-anchor="middle" class="rk-node__s">{{ n.sub }}</text>
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
