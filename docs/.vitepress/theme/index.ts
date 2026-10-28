import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import '@fontsource-variable/bricolage-grotesque/opsz.css'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/ibm-plex-sans/600.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './custom.css'
import RillHero from './components/RillHero.vue'
import RillConnect from './components/RillConnect.vue'
import RillFlow from './components/RillFlow.vue'
import RillRedis from './components/RillRedis.vue'
import RillBefore from './components/RillBefore.vue'
import RillSpec from './components/RillSpec.vue'
import RillStart from './components/RillStart.vue'
import RillDivider from './components/RillDivider.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RillHero', RillHero)
    app.component('RillConnect', RillConnect)
    app.component('RillFlow', RillFlow)
    app.component('RillRedis', RillRedis)
    app.component('RillBefore', RillBefore)
    app.component('RillSpec', RillSpec)
    app.component('RillStart', RillStart)
    app.component('RillDivider', RillDivider)
  },
} satisfies Theme
