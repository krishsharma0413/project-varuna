import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies /api to the API container (published on 127.0.0.1:8000 by docker compose),
// so the browser sees one origin and the session cookie works without CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
});
