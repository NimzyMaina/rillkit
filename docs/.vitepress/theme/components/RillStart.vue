<script setup lang="ts">
import { withBase } from 'vitepress'
</script>

<template>
  <section class="rk-start" aria-labelledby="rk-start-h">
    <div class="rk-wrap rk-start__grid">
      <div>
        <h2 id="rk-start-h" class="rk-h2">Running in about five minutes</h2>
        <p class="rk-sub">
          You need Python 3.9 or newer and a Redis you can reach. Local Docker is fine. The guide walks through the
          same steps with more explanation, then covers retries, the DLQ and running several workers.
        </p>
        <p class="rk-links">
          <a class="rk-btn rk-btn--primary" :href="withBase('/guide/getting-started')">Read the getting-started guide</a>
          <a :href="withBase('/examples/')">Examples</a>
          <a :href="withBase('/reference/broker')">API reference</a>
        </p>
      </div>
      <figure class="rk-term rk-term--plain" aria-label="Quick start commands">
        <div class="rk-term__bar"><span class="rk-term__tab">terminal</span></div>
        <pre><code><span class="c"># redis, if you do not have one</span>
<span class="p">$</span> docker run -d -p 6379:6379 redis:7

<span class="p">$</span> pip install rillkit
<span class="p">$</span> export REDIS_URL=redis://localhost:6379/0

<span class="p">$</span> python worker.py   <span class="c"># terminal 1</span>
<span class="p">$</span> python publish.py  <span class="c"># terminal 2</span></code></pre>
      </figure>
    </div>
  </section>
</template>
