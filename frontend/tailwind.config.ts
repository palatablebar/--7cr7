import type { Config } from 'tailwindcss'

// Only variable references here — every concrete colour lives in
// src/styles/tokens.css as an oklch() token.
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        paper: 'var(--paper)',
        'paper-2': 'var(--paper-2)',
        'paper-3': 'var(--paper-3)',
        rule: 'var(--rule)',
        'rule-soft': 'var(--rule-soft)',
        ink: 'var(--ink)',
        'ink-soft': 'var(--ink-soft)',
        'ink-faint': 'var(--ink-faint)',
        blue: 'var(--blue)',
        'blue-deep': 'var(--blue-deep)',
        rust: 'var(--rust)',
        ochre: 'var(--ochre)',
        sea: 'var(--sea)',
      },
      fontFamily: {
        display: ['Fraunces', '"Iowan Old Style"', 'Georgia', 'serif'],
        sans: ['Barlow', '"Helvetica Neue"', 'Helvetica', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"SFMono-Regular"', 'Menlo', 'monospace'],
      },
      letterSpacing: { label: '0.12em', wide: '0.05em' },
    },
  },
  plugins: [],
} satisfies Config
