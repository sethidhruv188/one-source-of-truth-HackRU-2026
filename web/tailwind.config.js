export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        ink:    { 900:"#0a0c10", 800:"#101419", 700:"#171c23", 600:"#1f262f", 500:"#2b333e" },
        line:   "#232a33",
        mist:   { 100:"#e8ecf1", 300:"#aeb8c4", 500:"#7a8696", 700:"#4a5563" },
        accent: { DEFAULT:"#4a8fe7", dim:"#2f5f9e", soft:"rgba(74,143,231,.12)" },
        good:   "#3fa776",
        warn:   "#c99a3c",
        bad:    "#cf5f58",
      },
      boxShadow: { panel: "0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.35)" },
    },
  },
  plugins: [],
};
