/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#080c14',
        surface:  '#0d1420',
        surface2: '#111827',
        border:   '#1e2d45',
        border2:  '#243550',
        dim:      '#4e6480',
        mid:      '#7a9ab8',
        text:     '#c9d8ee',
        blue:     '#1e6fff',
        green:    '#00d68f',
        yellow:   '#ffc53d',
        orange:   '#ff7b2e',
        red:      '#ff4d4d',
        purple:   '#a855f7',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
