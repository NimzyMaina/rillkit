<template>
  <section class="rk-section rk-code" aria-labelledby="rk-code-h">
    <div class="rk-wrap">
      <header class="rk-head">
        <p class="rk-kicker">Two files, one stream</p>
        <h2 id="rk-code-h" class="rk-h2">Publish on one side. <em>Consume</em> on the other.</h2>
        <p class="rk-sub">
          No schemas to register and no consumer loop to write. Name a stream and a group, decorate a function, call run.
        </p>
      </header>
      <div class="rk-panels">
        <figure class="rk-panel rk-panel--a">
          <figcaption><i class="rk-fdot rk-fdot--pink" />publish.py</figcaption>
          <div class="vp-doc"><slot name="publish" /></div>
        </figure>
        <svg class="rk-link" viewBox="0 0 80 200" aria-hidden="true" preserveAspectRatio="none">
          <path d="M0 100 C 26 40, 54 160, 80 100" />
          <path d="M0 100 C 26 40, 54 160, 80 100" class="flow" />
        </svg>
        <figure class="rk-panel rk-panel--b">
          <figcaption><i class="rk-fdot rk-fdot--cyan" />worker.py</figcaption>
          <div class="vp-doc"><slot name="consume" /></div>
        </figure>
      </div>
    </div>
  </section>
</template>
