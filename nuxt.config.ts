// Site estático (SPA): tudo roda no navegador, que fala com o Companion pelo Web Bluetooth.
export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',
  ssr: false,
  devtools: { enabled: false },
  app: {
    head: {
      title: 'Claude Code Companion',
      htmlAttrs: { lang: 'pt-BR' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content: 'Portal do Claude Code Companion: conecte pelo Bluetooth, veja a bateria e ajuste volume e brilho.',
        },
        { name: 'theme-color', content: '#111315' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: 'logo.svg' },
        { rel: 'apple-touch-icon', href: 'apple-touch-icon.png' },
      ],
    },
  },
})
