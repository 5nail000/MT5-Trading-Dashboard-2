import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Night palette
        background: "#0f0f0f",
        surface: "#1a1a1a",
        surfaceHover: "#252525",
        border: "#2a2a2a",
        textPrimary: "#e5e5e5",
        textSecondary: "#a3a3a3",
        positive: "#22c55e",
        negative: "#ef4444",
        neutral: "#3b82f6",
        warning: "#f59e0b",
      },
    },
  },
  plugins: [],
} satisfies Config;
