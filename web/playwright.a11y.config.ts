import { defineConfig } from "@playwright/test";

const baseURL = "http://kynetic.localhost:3199";
export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL,
    launchOptions: {
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
        : {}),
      args: ["--host-resolver-rules=MAP kynetic.localhost 127.0.0.1"],
    },
  },
  webServer: {
    command: "NEXT_PUBLIC_USE_MOCKS=true npm run dev -- --hostname 127.0.0.1 --port 3199",
    url: "http://127.0.0.1:3199",
    reuseExistingServer: false,
  },
});
