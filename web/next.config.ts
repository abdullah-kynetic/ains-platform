import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants.js";
import { checkBuildMode } from "./scripts/build-guard.mjs";

const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: { position: "bottom-right" },
  poweredByHeader: false,
  // Dev already allows *.localhost. These let Playwright open production-style hosts.
  allowedDevOrigins: ["127.0.0.1", "kiensolutions.com", "*.kiensolutions.com"],
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
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
