import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.25rem", screens: { "2xl": "1200px" } },
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-secondary)",
        fg: "var(--text-primary)",
        "fg-2": "var(--text-secondary)",
        muted: "var(--text-muted)",
        line: "var(--border)",
        "line-strong": "var(--border-strong)",
        ink: "var(--black)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "display": ["clamp(2.75rem, 7vw, 5.5rem)", { lineHeight: "0.98", letterSpacing: "-0.045em" }],
        "title": ["clamp(2rem, 4.2vw, 3.25rem)", { lineHeight: "1.05", letterSpacing: "-0.035em" }],
      },
      borderRadius: { xl: "14px", "2xl": "18px" },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.04), 0 4px 16px -6px rgba(0,0,0,0.06)",
        lift: "0 2px 4px rgba(0,0,0,0.04), 0 12px 32px -12px rgba(0,0,0,0.12)",
      },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        "fade-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: {
        shimmer: "shimmer 1.6s infinite",
        "fade-up": "fade-up .5s cubic-bezier(.2,.7,.2,1) both",
      },
    },
  },
  plugins: [],
};
export default config;
