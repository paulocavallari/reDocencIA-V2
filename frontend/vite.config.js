import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("react-quill") || id.includes("quill")) {
            return "editor";
          }
          if (id.includes("@supabase/supabase-js")) {
            return "supabase";
          }
          if (id.includes("pdfjs-dist")) {
            return "pdfjs";
          }
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
});
