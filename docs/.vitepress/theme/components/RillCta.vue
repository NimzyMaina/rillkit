<script setup lang="ts">
import { withBase } from 'vitepress'
import RillArt from './RillArt.vue'
import CopyInstall from './CopyInstall.vue'
</script>

<template>
  <section class="rk-cta">
    <RillArt uid="cta" :seed="29" :trunks="[0.5]" :max-paths="46" :bounds="[0.1, 0.9]" />
    <div class="rk-cta__inner">
      <h2 class="rk-h2">Let the messages <em>find their way.</em></h2>
      <p class="rk-sub">Install it, point it at Redis, and have a worker running before your coffee cools.</p>
      <div class="rk-actions rk-actions--center">
        <a class="rk-btn rk-btn--primary" :href="withBase('/guide/getting-started')">Get started</a>
        <a class="rk-btn rk-btn--ghost" :href="withBase('/examples/')">Browse examples</a>
        <a class="rk-btn rk-btn--ghost" :href="withBase('/reference/broker')">API reference</a>
      </div>
      <CopyInstall />
    </div>
  </section>
</template>
