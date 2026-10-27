<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'
import RillArt from './RillArt.vue'
import CopyInstall from './CopyInstall.vue'

const root = ref<HTMLElement | null>(null)
let raf = 0
let io: IntersectionObserver | undefined
let tx = 0, ty = 0, cx = 0, cy = 0, sy = 0
let visible = true
let reduce = false

function frame() {
  raf = 0
  const el = root.value
  if (!el) return
  cx += (tx - cx) * 0.08
  cy += (ty - cy) * 0.08
  el.style.setProperty('--mx', cx.toFixed(3))
  el.style.setProperty('--my', cy.toFixed(3))
  el.style.setProperty('--sy', sy.toFixed(1))
  if (visible && (Math.abs(tx - cx) > 0.002 || Math.abs(ty - cy) > 0.002)) raf = requestAnimationFrame(frame)
}
const kick = () => { if (!raf && visible) raf = requestAnimationFrame(frame) }
function onMove(e: PointerEvent) {
  if (reduce || e.pointerType === 'touch') return
  const r = root.value!.getBoundingClientRect()
  tx = ((e.clientX - r.left) / r.width - 0.5) * 2
  ty = ((e.clientY - r.top) / r.height - 0.5) * 2
  kick()
}
function onScroll() {
  if (reduce || !visible) return
  sy = Math.min(window.scrollY, 900)
  kick()
  if (!raf) frame()
}

onMounted(() => {
  reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce) return
  window.addEventListener('scroll', onScroll, { passive: true })
  io = new IntersectionObserver(([en]) => {
    visible = en.isIntersecting
    root.value?.classList.toggle('is-paused', !visible)
  })
  io.observe(root.value!)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  io?.disconnect()
  cancelAnimationFrame(raf)
})
</script>

<template>
  <section ref="root" class="rk-hero" @pointermove="onMove">
    <RillArt uid="hero" :seed="11" :trunks="[0.52, 0.74, 0.9]" :max-paths="58" />
    <div class="rk-hero__inner">
      <div class="rk-hero__copy">
        <p class="rk-eyebrow"><span class="rk-dot" />Python &middot; Redis Streams</p>
        <h1 class="rk-title">Redis Streams<br />that <em>flow.</em></h1>
        <p class="rk-lede">
          Publish and consume with consumer groups, retries, a dead-letter queue and middleware.
          A few lines of plain Python, and your messages find their way downhill.
        </p>
        <div class="rk-actions">
          <a class="rk-btn rk-btn--primary" :href="withBase('/guide/getting-started')">
            Get started
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          </a>
          <a class="rk-btn rk-btn--ghost" href="https://github.com/NimzyMaina/rillkit" target="_blank" rel="noopener">
            <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" /></svg>
            GitHub
          </a>
        </div>
        <CopyInstall />
      </div>
      <aside class="rk-log" aria-hidden="true">
        <div class="rk-log__bar"><i /><i /><i /><span>worker.log</span></div>
        <ol>
          <li><b class="t-cyan">recv</b> orders <s>1718-0</s> <span>group=workers</span></li>
          <li><b class="t-ok">ack</b> orders <s>1718-0</s></li>
          <li><b class="t-cyan">recv</b> orders <s>1719-0</s></li>
          <li><b class="t-warn">retry</b> 2/3 <span>backoff 4s</span></li>
          <li><b class="t-pink">dlq</b> orders-dlq <span>x-error=timeout</span></li>
        </ol>
      </aside>
    </div>
  </section>
</template>
