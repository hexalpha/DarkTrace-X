import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#060912",
        panel: "#0c1220",
        cyan: "#67e8f9",
        violet: "#a78bfa"
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(103,232,249,.10), 0 16px 48px rgba(0,0,0,.32)"
      }
    }
  },
  plugins: []
};

export default config;

