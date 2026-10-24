import { defineConfig } from "@playwright/test";

const landingServer = {
  command: "python3 -m http.server 3110 --bind 127.0.0.1",
  cwd: "../landing/public",
  url: "http://127.0.0.1:3110",
  reuseExistingServer: !process.env.CI,
};

const portalServer = {
  command:
    "NEXT_PUBLIC_USE_MOCKS=true npm run dev -- --hostname 127.0.0.1 --port 3100",
  url: "http://127.0.0.1:3100",
  reuseExistingServer: !process.env.CI,
};

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {},
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? landingServer
    : [portalServer, landingServer],
});
