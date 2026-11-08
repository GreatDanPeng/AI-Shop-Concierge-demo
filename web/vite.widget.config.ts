import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The widget is one self-contained script (React included) that any page can load with a single
// <script> tag. It is built into public/ so the shop build copies it next to index.html.
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "public",
    emptyOutDir: false,
    copyPublicDir: false,
    cssCodeSplit: false,
    lib: {
      entry: "src/widget/entry.tsx",
      name: "ConciergeWidget",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
  },
});
