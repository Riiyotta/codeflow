/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  // Webflow's normalize (src/styles/webflow.css) is the base layer, as on the original.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        black: '#0c0c0c',
        pink: '#f5d0e6',
        grey: '#707070',
        dark: '#181818',
        gl: '#0f0f0f',
      },
      fontFamily: {
        sans: ['"Helvetica Neue"', 'Arial', 'sans-serif'],
        cond: ['"Helvetica Neue Condensed"', 'Arial', 'sans-serif'],
        fira: ['Firacode', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
