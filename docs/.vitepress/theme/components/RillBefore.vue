<script setup lang="ts">
import { withBase } from 'vitepress'
</script>

<template>
  <section class="rk-before" aria-labelledby="rk-before-h">
    <div class="rk-wrap">
      <div class="rk-before__head">
        <h2 id="rk-before-h" class="rk-h2">The loop you would have written</h2>
        <p class="rk-sub">
          Most teams start with <code>xreadgroup</code> in a <code>while True</code>. It works until the first exception.
          The <a :href="withBase('/examples/migrating-from-raw-redis-py')">migration example</a> runs both versions side by side.
        </p>
      </div>
      <div class="rk-before__grid">
        <figure class="rk-win vp-doc rk-win--raw"><slot name="before" /></figure>
        <div class="rk-before__right">
          <figure class="rk-win vp-doc rk-win--rk"><slot name="after" /></figure>
          <ul class="rk-gaps">
            <li>Entries stuck with a crashed worker are never claimed again.</li>
            <li>A handler that keeps failing keeps failing. There is no retry limit and no backoff.</li>
            <li>Nothing goes to a dead-letter stream, so bad messages pile up in the pending list.</li>
            <li>Ctrl-C drops whatever was in flight.</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
