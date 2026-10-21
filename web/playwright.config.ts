import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://127.0.0.1:3010",
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
  webServer: {
    command: "NEXT_PUBLIC_USE_MOCKS=true npm run dev -- --hostname 127.0.0.1 --port 3010",
    url: "http://127.0.0.1:3010", timeout: 120000,
  },
});
