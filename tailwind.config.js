// prettier-ignore

/** @type {import('tailwindcss').Config} */

module.exports = {
  content: [
    './templates/**/*.html',
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("daisyui"),
    require('@tailwindcss/typography'),
    require("@tailwindcss/forms"),
  ],
}
