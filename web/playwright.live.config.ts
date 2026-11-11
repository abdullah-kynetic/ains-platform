import { defineConfig } from "@playwright/test";

/**
 * Sign-in end to end against the REAL local backend (scripts/e2e_backend.py) with synthetic
 * users. No mocks: NEXT_PUBLIC_USE_MOCKS is unset, so the app calls /auth/* on the API.
 * Run: npm run test:e2e:live   (needs the Python venv at the repo root)
 */
export default defineConfig({
  testDir: "./e2e-live",
  timeout: 60_000,
  workers: 1,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://kynetic.localhost:3100",
    launchOptions: {
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
        : {}),
    },
  },
  webServer: [
    {
      command: "PYTHONPATH=. .venv/bin/python scripts/e2e_backend.py --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command:
        "NEXT_PUBLIC_USE_MOCKS= NEXT_PUBLIC_API_URL=http://{portal}:8000 npm run dev -- --hostname 0.0.0.0 --port 3100",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
