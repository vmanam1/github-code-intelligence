/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        editor: {
          bg: "#1e1e1e",
          fg: "#d4d4d4",
          sidebar: "#252526",
          activity: "#333333",
          border: "#303030",
          accent: "#007acc",
          accentHover: "#0062a3",
          active: "#37373d",
          inactive: "#2d2d2d",
          hover: "#2a2d2e",
        }
      }
    },
  },
  plugins: [],
}
