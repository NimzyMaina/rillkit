<script setup lang="ts">
import { makeRills } from '../rill'

interface Feat {
  title: string
  body: string
  span: string
  tone: 'cyan' | 'indigo' | 'pink' | 'teal' | 'amber'
  chips?: string[]
  code?: string
}

const feats: Feat[] = [
  {
    title: 'Consumer groups done right',
    body: 'Groups are created for you, every worker gets its own consumer name, and entries stuck with a crashed worker are claimed back once they sit idle.',
    span: 'a', tone: 'cyan',
  },
  {
    title: 'At-least-once, with retries and backoff',
    body: 'A failing message comes back after an exponential backoff, up to max_retries. Nothing vanishes quietly.',
    span: 'b', tone: 'indigo',
  },
  {
    title: 'Dead-letter queue with context',
    body: 'When retries run out the entry moves to a DLQ stream along with the error, the original id, the group and the delivery count. replay_dlq() sends it back.',
    span: 'b', tone: 'pink',
  },
  {
    title: 'Ack policies',
    body: 'Decide what happens when a handler finishes. The default retries on error, and you can opt out.',
    span: 'c', tone: 'amber',
    chips: ['NACK_ON_ERROR', 'ACK_ALWAYS', 'ACK_FIRST', 'MANUAL'],
  },
  {
    title: 'Middleware hooks',
    body: 'Wrap receiving, handling, publishing and cleanup. Idempotent ships in the box to skip duplicate deliveries.',
    span: 'd', tone: 'teal',
  },
  {
    title: 'Startup and shutdown hooks',
    body: 'on_startup, after_startup, on_shutdown and after_shutdown, as plain decorators.',
    span: 'e', tone: 'cyan',
  },
  {
    title: 'Plain dicts, Pydantic if you like',
    body: 'Handlers receive decoded JSON as a dict. Annotate the parameter with a Pydantic model and it is validated for you.',
    span: 'd', tone: 'indigo',
  },
  {
    title: 'Graceful shutdown and heartbeat',
    body: 'SIGINT and SIGTERM let in-flight messages finish. Live workers publish a heartbeat you can read with active_workers().',
    span: 'd', tone: 'pink',
  },
  {
    title: 'Interoperable wire format',
    body: 'One JSON string in the data field of an ordinary stream entry. Anything that speaks Redis can read it or write it.',
    span: 'd', tone: 'teal',
  },
]

const arts = feats.map((_, i) =>
  makeRills(31 + i * 7, { width: 320, height: 220, trunks: [0.55 + ((i * 37) % 30) / 100], maxPaths: 11, step: 12 }),
)
</script>

<template>
  <section class="rk-section rk-features" aria-labelledby="rk-feat-h">
    <div class="rk-wrap">
      <header class="rk-head">
        <p class="rk-kicker">What you get</p>
        <h2 id="rk-feat-h" class="rk-h2">The boring parts, <em>handled</em>.</h2>
        <p class="rk-sub">Redis Streams give you the channel. rillkit digs the rest of the bed.</p>
      </header>
      <ul class="rk-grid">
        <li v-for="(f, i) in feats" :key="f.title" class="rk-card" :class="[`rk-card--${f.span}`, `tone-${f.tone}`]">
          <svg class="rk-card__art" viewBox="0 0 320 220" preserveAspectRatio="xMaxYMax slice" aria-hidden="true">
            <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
              <path v-for="(p, k) in arts[i]" :key="k" :d="p.d" :stroke-width="p.w * 0.8" />
            </g>
            <g class="rk-card__flow" fill="none" stroke-linecap="round">
              <path v-for="(p, k) in arts[i]" :key="k" :d="p.d" :stroke-width="Math.max(0.6, p.w * 0.35)" :style="{ animationDuration: p.dur + 's' }" />
            </g>
          </svg>
          <h3>{{ f.title }}</h3>
          <p>{{ f.body }}</p>
          <ul v-if="f.chips" class="rk-chips">
            <li v-for="c in f.chips" :key="c"><code>{{ c }}</code></li>
          </ul>
        </li>
      </ul>
    </div>
  </section>
</template>
