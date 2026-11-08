import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development the API is the FastAPI server; proxying keeps everything on one origin, so the
// demo sign-in cookie works exactly as it does in production (where FastAPI serves this build).
const API = "http://127.0.0.1:8000";
const API_PATHS = ["/me", "/discounts", "/estimate", "/chat", "/health", "/demo"];

export default defineConfig({
  plugins: [react()],
  server: { proxy: Object.fromEntries(API_PATHS.map((path) => [path, API])) },
  test: {
    environment: "jsdom",
    css: true, // so the widget's inlined stylesheet is real text in tests, not an empty string
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test-setup.ts"],
  },
});
