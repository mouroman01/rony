import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    open: true,
    host: "0.0.0.0",
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three"],
        },
      },
    },
  },
});
