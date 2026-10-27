<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{ command?: string }>(), { command: 'pip install rillkit' })
const copied = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.command)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = props.command
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    ta.remove()
  }
  copied.value = true
  clearTimeout(timer)
  timer = setTimeout(() => (copied.value = false), 1800)
}
</script>

<template>
  <div class="rk-install">
    <span class="rk-install__prompt" aria-hidden="true">$</span>
    <code>{{ command }}</code>
    <button type="button" class="rk-install__btn" :aria-label="`Copy: ${command}`" @click="copy">
      <svg v-if="!copied" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="9" y="9" width="11" height="11" rx="2.5" /><path d="M5 15V6.5A2.5 2.5 0 0 1 7.5 4H15" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 12.5l4.5 4.5L19 7.5" />
      </svg>
      <span class="rk-install__label">{{ copied ? 'Copied' : 'Copy' }}</span>
    </button>
    <span class="sr-only" role="status" aria-live="polite">{{ copied ? 'Copied to clipboard' : '' }}</span>
  </div>
</template>
