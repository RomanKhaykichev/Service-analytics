import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: true,
    port: 8080,
    allowedHosts: ["profiboard.uz", "www.profiboard.uz"],
    proxy: {
      "/api": {
        // In dev always proxy to local API so login works without setting VITE_API_URL
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 8080,
    allowedHosts: ["profiboard.uz", "www.profiboard.uz"],
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
