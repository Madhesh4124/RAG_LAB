import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react({ jsxImportSource: "react" })],
  test: {
    environment: "jsdom",
    setupFiles: "./src/__tests__/setupTests.js",
    globals: true,
  },
});
