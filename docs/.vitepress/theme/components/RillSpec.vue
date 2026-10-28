<script setup lang="ts">
import { withBase } from 'vitepress'

const failure = [
  { tone: 'blue', t: 'Consumer groups', d: 'The group is created for you and every worker gets its own consumer name. Entries left with a crashed worker are claimed back once they have sat idle long enough.' },
  { tone: 'amber', t: 'Retries with backoff', d: 'A failing message comes back after an exponential backoff, up to max_retries. The default is 3, so a handler runs at most four times for one message.' },
  { tone: 'amber', t: 'nack or reject', d: 'msg.nack() asks for another attempt. msg.reject("reason") says this one can never work and skips the remaining retries.' },
  { tone: 'coral', t: 'Dead-letter stream', d: 'Entries that run out of retries, or are rejected, move to <stream>-dlq with the error, original id, group and delivery count. broker.replay_dlq() puts them back.' },
]

const policies = [
  { n: 'NACK_ON_ERROR', tag: 'default', ret: 'ack', raise: 'retry', note: 'At-least-once. Failures are retried, then dead-lettered.' },
  { n: 'ACK_ALWAYS', ret: 'ack', raise: 'ack', note: 'Failures are logged and dropped, never retried.' },
  { n: 'ACK_FIRST', ret: 'acked before', raise: 'acked before', note: 'At-most-once. A crash mid-handler loses the message.' },
  { n: 'MANUAL', ret: 'you call msg.ack()', raise: 'retry', note: 'RillKit never acks. Return without acking and it is retried.' },
]

const cls = (v: string) => (v === 'ack' ? 'is-ok' : v === 'retry' ? 'is-retry' : '')

const around = [
  { t: 'Middleware', d: 'Hooks for receiving, handling, publishing and cleanup. Idempotent ships in the box and skips duplicate deliveries.' },
  { t: 'Startup and shutdown hooks', d: 'on_startup, after_startup, on_shutdown and after_shutdown, as plain decorators on the broker.' },
  { t: 'Dicts or Pydantic', d: 'Handlers get the decoded JSON as a dict. Annotate the parameter with a Pydantic model and it is validated before your code runs. Pydantic is optional.' },
  { t: 'Graceful shutdown, heartbeat', d: 'SIGINT and SIGTERM let in-flight messages finish. Each consumer refreshes a heartbeat key, and active_workers() reads them.' },
  { t: 'Plain wire format', d: 'One JSON string in the data field of an ordinary stream entry. Anything that can XADD can publish, and anything that can XREADGROUP can read.' },
]
</script>

<template>
  <section class="rk-spec" aria-labelledby="rk-spec-h">
    <div class="rk-wrap">
      <h2 id="rk-spec-h" class="rk-h2 rk-spec__h">What happens when a handler fails</h2>
      <ul class="rk-fail">
        <li v-for="f in failure" :key="f.t" :class="`tone-${f.tone}`">
          <h3>{{ f.t }}</h3>
          <p>{{ f.d }}</p>
        </li>
      </ul>

      <div class="rk-policies">
        <div class="rk-policies__intro">
          <h3 class="rk-h3">Ack policies</h3>
          <p>Choose when a message counts as done. Set it per handler with <code>ack_policy=</code>.
            <a :href="withBase('/guide/ack-policies')">Details</a></p>
        </div>
        <table>
          <thead><tr><th>Policy</th><th>Handler returns</th><th>Handler raises</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in policies" :key="p.n">
              <td><code class="rk-pol">{{ p.n }}</code><span v-if="p.tag" class="rk-tag">{{ p.tag }}</span></td>
              <td data-l="Returns" :class="cls(p.ret)">{{ p.ret }}</td>
              <td data-l="Raises" :class="cls(p.raise)">{{ p.raise }}</td>
              <td class="rk-pol__note">{{ p.note }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rk-around">
        <h3 class="rk-h3">Around the handler</h3>
        <dl>
          <div v-for="a in around" :key="a.t">
            <dt>{{ a.t }}</dt>
            <dd>{{ a.d }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>
