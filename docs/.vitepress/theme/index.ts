import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/manrope/index.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './custom.css'
import RillHero from './components/RillHero.vue'
import RillCode from './components/RillCode.vue'
import RillFeatures from './components/RillFeatures.vue'
import RillFlow from './components/RillFlow.vue'
import RillCta from './components/RillCta.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RillHero', RillHero)
    app.component('RillCode', RillCode)
    app.component('RillFeatures', RillFeatures)
    app.component('RillFlow', RillFlow)
    app.component('RillCta', RillCta)
  },
} satisfies Theme
