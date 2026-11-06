import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [vue(), {
    name: "public-annotator-entry",
    transformIndexHtml: {
      order: "pre",
      handler(html) {
        return mode === "public"
          ? html.replace("/src/main.ts", "/src/main.public.ts").replace("Administrator Portal", "Annotation")
          : html;
      },
    },
    generateBundle(_options, bundle) {
      if (mode !== "public") return;
      for (const output of Object.values(bundle)) {
        if (output.type !== "chunk") continue;
        for (const id of Object.keys(output.modules)) {
          if (/layouts\/AdminLayout|pages\/dashboard|pages\/views\/(Training|Datasets|Models|PilotResults)|router\/index/.test(id.replaceAll("\\", "/"))) {
            this.error(`Admin module included in public build: ${id}`);
          }
        }
      }
    },
  }],
  build: { outDir: mode === "public" ? "dist-public" : "dist-private" },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
}));
