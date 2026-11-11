import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants.js";
import { checkBuildMode } from "./scripts/build-guard.mjs";
import { securityHeaders } from "./scripts/security-headers.mjs";


const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: { position: "bottom-right" },
  poweredByHeader: false,
  // Dev already allows *.localhost. These let Playwright open production-style hosts.
  allowedDevOrigins: ["127.0.0.1", "kiensolutions.com", "*.kiensolutions.com"],
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders(process.env, process.env.NODE_ENV === "development") }];
  },
};

/** `next build` refuses a demo (mock) build that was not declared as the demo, and a production build with mocks. */
export default function config(phase: string): NextConfig {
  if (phase === PHASE_PRODUCTION_BUILD) {
    const problem = checkBuildMode(process.env);
    if (problem) throw new Error(`Build refused: ${problem}`);
  }
  return nextConfig;
}
