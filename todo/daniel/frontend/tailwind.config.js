/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bull: "#ef4444",
        bear: "#10b981",
      },
    },
  },
  plugins: [],
};
