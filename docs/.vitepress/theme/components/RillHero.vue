<script setup lang="ts">
import { withBase } from 'vitepress'
import RillArt from './RillArt.vue'
import CopyInstall from './CopyInstall.vue'

interface Row { t: string; lv: 'info' | 'out' | 'retry' | 'dlq'; label: string; msg: string }
const rows: Row[] = [
  { t: '12:04:01', lv: 'info', label: 'INFO', msg: 'consumer started | stream: orders | group: workers | policy: nack_on_error | max retries: 3' },
  { t: '12:04:02', lv: 'out', label: 'stdout', msg: 'charged order 1' },
  { t: '12:04:02', lv: 'out', label: 'stdout', msg: 'charged order 2' },
  { t: '12:04:03', lv: 'retry', label: 'ERROR', msg: 'handler failed for message 1730032643012-0 (delivery 1): card declined' },
  { t: '12:04:09', lv: 'retry', label: 'ERROR', msg: 'handler failed for message 1730032643012-0 (delivery 2): card declined' },
  { t: '12:04:21', lv: 'out', label: 'stdout', msg: 'charged order 3' },
  { t: '12:04:21', lv: 'dlq', label: 'WARNING', msg: 'moving message 1730032645250-0 to orders-dlq: bad total' },
]
</script>

<template>
  <section class="rk-hero">
    <RillArt :seed="11" :trunks="[0.52, 0.7, 0.88]" :max-paths="18" />
    <span class="rk-reg rk-reg--tl" aria-hidden="true" /><span class="rk-reg rk-reg--br" aria-hidden="true" />
    <div class="rk-hero__inner">
      <div class="rk-hero__copy">
        <h1 class="rk-title">Consume Redis Streams without writing the&nbsp;loop.</h1>
        <p class="rk-lede">
          RillKit is a Python library on top of redis-py. You name a stream and a group, decorate a function and call
          <code>run()</code>. Consumer groups, retries with backoff, a dead-letter queue and a clean shutdown come with it.
        </p>
        <div class="rk-actions">
          <a class="rk-btn rk-btn--primary" :href="withBase('/guide/getting-started')">Get started</a>
          <a class="rk-btn rk-btn--ghost" href="https://github.com/NimzyMaina/rillkit" target="_blank" rel="noopener">
            <svg viewBox="0 0 16 16" width="17" height="17" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" /></svg>
            Source
          </a>
        </div>
        <CopyInstall />
        <p class="rk-meta">Python 3.9+ <i /> MIT <i /> one dependency: redis-py</p>
      </div>

      <figure class="rk-term" aria-label="Sample worker output">
        <div class="rk-term__bar"><span class="rk-term__tab">python worker.py</span></div>
        <ol>
          <li v-for="(r, i) in rows" :key="i" :style="{ '--i': i }">
            <time>{{ r.t }}</time><b :class="`lv-${r.lv}`">{{ r.label }}</b><span>{{ r.msg }}</span>
          </li>
          <li class="rk-term__cur" :style="{ '--i': rows.length }"><time>12:04:22</time><b class="lv-cur" /><span class="rk-caret" /></li>
        </ol>
      </figure>
    </div>
  </section>
</template>
