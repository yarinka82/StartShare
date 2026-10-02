import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The SPA talks to Django through the dev proxy, so cookies and CSRF stay same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
