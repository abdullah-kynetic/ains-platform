import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://kynetic.localhost:3100";
const localServer = !process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL,
    launchOptions: {
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
        : {}),
      // Production-style hosts in the tenant tests resolve to this machine.
      args: [
        "--host-resolver-rules=MAP kiensolutions.com 127.0.0.1, MAP www.kiensolutions.com 127.0.0.1, MAP kynetic.kiensolutions.com 127.0.0.1",
      ],
    },
  },
  webServer: localServer
    ? {
        command:
          "NEXT_PUBLIC_USE_MOCKS=true npm run dev -- --hostname 0.0.0.0 --port 3100",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
      }
    : undefined,
});
