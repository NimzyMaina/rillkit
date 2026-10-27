import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'rillkit',
  description: 'Simple publish and consume for Redis Streams',
  base: '/rillkit/',
  cleanUrls: true,
  lastUpdated: true,

  head: [['link', { rel: 'icon', href: '/rillkit/logo.svg' }]],

  markdown: {
    lineNumbers: false,
  },

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/getting-started', activeMatch: '/guide/' },
      { text: 'Examples', link: '/examples/', activeMatch: '/examples/' },
      { text: 'Reference', link: '/reference/broker', activeMatch: '/reference/' },
      { text: 'PyPI', link: 'https://pypi.org/project/rillkit/' },
      { text: 'GitHub', link: 'https://github.com/NimzyMaina/rillkit' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Start here',
          items: [
            { text: 'Getting started', link: '/guide/getting-started' },
            { text: 'Concepts', link: '/guide/concepts' },
          ],
        },
        {
          text: 'Using rillkit',
          items: [
            { text: 'Publishing', link: '/guide/publishing' },
            { text: 'Consuming', link: '/guide/consuming' },
            { text: 'Ack policies', link: '/guide/ack-policies' },
            { text: 'Retries and the DLQ', link: '/guide/retries-and-dlq' },
            { text: 'Middleware', link: '/guide/middleware' },
            { text: 'Pydantic models', link: '/guide/pydantic' },
          ],
        },
        {
          text: 'Running it',
          items: [
            { text: 'Lifecycle', link: '/guide/lifecycle' },
            { text: 'Configuration', link: '/guide/configuration' },
            { text: 'Operations', link: '/guide/operations' },
            { text: 'Testing', link: '/guide/testing' },
          ],
        },
      ],
      '/examples/': [
        {
          text: 'Examples',
          items: [
            { text: 'Overview', link: '/examples/' },
            { text: 'Basic worker', link: '/examples/basic-worker' },
            { text: 'Two-stage pipeline', link: '/examples/pipeline' },
            { text: 'Pydantic models', link: '/examples/pydantic-models' },
            { text: 'Retries and DLQ', link: '/examples/retries-and-dlq' },
            { text: 'Reject vs nack', link: '/examples/reject-vs-nack' },
            { text: 'Manual ack', link: '/examples/manual-ack' },
            { text: 'Timing and idempotency', link: '/examples/middleware-timing-and-idempotency' },
            { text: 'Multiple workers', link: '/examples/multiple-workers' },
            { text: 'Graceful shutdown', link: '/examples/graceful-shutdown' },
            { text: 'FastAPI publisher', link: '/examples/fastapi-publisher' },
            { text: 'Migrating from redis-py', link: '/examples/migrating-from-raw-redis-py' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'API reference',
          items: [
            { text: 'Broker', link: '/reference/broker' },
            { text: 'Stream', link: '/reference/stream' },
            { text: 'Message', link: '/reference/message' },
            { text: 'AckPolicy', link: '/reference/ack-policy' },
            { text: 'Middleware', link: '/reference/middleware' },
            { text: 'Settings', link: '/reference/settings' },
            { text: 'Exceptions', link: '/reference/exceptions' },
          ],
        },
      ],
    },

    search: { provider: 'local' },

    editLink: {
      pattern: 'https://github.com/NimzyMaina/rillkit/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/NimzyMaina/rillkit' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © Nimrod Maina',
    },

    outline: [2, 3],
  },
})
