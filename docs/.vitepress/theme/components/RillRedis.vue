<template>
  <section class="rk-redis" aria-labelledby="rk-redis-h">
    <div class="rk-wrap rk-redis__grid">
      <div class="rk-redis__text">
        <h2 id="rk-redis-h" class="rk-h2">Nothing hidden. Look in Redis.</h2>
        <p class="rk-sub">
          Groups, pending entries and the dead-letter stream are ordinary Redis structures. When something looks off at 2am,
          <code>redis-cli</code> shows you what RillKit sees.
        </p>
        <dl class="rk-notes">
          <div class="is-ok">
            <dt>Acked</dt>
            <dd>The entry is acked with <code>XACK</code> and leaves the pending list. <code>lag: 0</code> means the group has read everything.</dd>
          </div>
          <div class="is-retry">
            <dt>Waiting to retry</dt>
            <dd>Still pending, with a delivery count. It is claimed again once it has been idle for <code>claim_idle_ms</code> times the backoff.</dd>
          </div>
          <div class="is-dlq">
            <dt>Dead-lettered</dt>
            <dd>Copied to <code>orders-dlq</code> with the original body plus five <code>x-</code> fields saying where it came from and why it stopped.</dd>
          </div>
        </dl>
      </div>

      <figure class="rk-term rk-term--cli" aria-label="redis-cli session showing a consumer group, a pending entry and a dead-letter entry">
        <div class="rk-term__bar"><span class="rk-term__tab">redis-cli</span></div>
        <pre><code><span class="p">127.0.0.1:6379&gt;</span> <b>XINFO GROUPS orders</b>
1)  1) <span class="k">"name"</span>
    2) <span class="s">"workers"</span>
    3) <span class="k">"consumers"</span>
    4) (integer) <span class="n">2</span>
    5) <span class="k">"pending"</span>
    6) (integer) <span class="n is-retry">1</span>
    7) <span class="k">"last-delivered-id"</span>
    8) <span class="s">"1730032645250-0"</span>
    9) <span class="k">"entries-read"</span>
   10) (integer) <span class="n">7</span>
   11) <span class="k">"lag"</span>
   12) (integer) <span class="n is-ok">0</span>

<span class="p">127.0.0.1:6379&gt;</span> <b>XPENDING orders workers - + 10</b>
1) 1) <span class="s">"1730032643012-0"</span>
   2) <span class="s">"workers-web1-4242"</span>
   3) (integer) <span class="n">6210</span>
   4) (integer) <span class="n is-retry">2</span>

<span class="p">127.0.0.1:6379&gt;</span> <b>XRANGE orders-dlq - + COUNT 1</b>
1) 1) <span class="s">"1730032645261-0"</span>
   2) 1) <span class="k">"data"</span>
      2) <span class="s">"{\"id\": 7, \"total\": -5}"</span>
      3) <span class="k is-dlq">"x-original-id"</span>
      4) <span class="s">"1730032645250-0"</span>
      5) <span class="k is-dlq">"x-stream"</span>
      6) <span class="s">"orders"</span>
      7) <span class="k is-dlq">"x-group"</span>
      8) <span class="s">"workers"</span>
      9) <span class="k is-dlq">"x-error"</span>
     10) <span class="s">"bad total"</span>
     11) <span class="k is-dlq">"x-deliveries"</span>
     12) <span class="s">"1"</span></code></pre>
      </figure>
    </div>
  </section>
</template>
