import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        google: {
          blue: "#1a73e8",
          green: "#1e8e3e",
          yellow: "#f9ab00",
          red: "#d93025",
          dark: "#202124",
        },
      },
    },
  },
  plugins: [],
};

export default config;
