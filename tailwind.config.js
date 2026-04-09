// This project uses Tailwind CSS v4 (shipped by `pytailwindcss`).
// Tailwind v4 is CSS-first: configuration lives in
// `src/app/static/css/tailwind.src.css` via `@source` and `@theme` directives,
// not in this file. This file is kept only as a marker for tooling.
//
// To recompile:
//   uv run tailwindcss -i src/app/static/css/tailwind.src.css -o src/app/static/css/tailwind.css --minify
//
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/app/templates/**/*.html"],
};
