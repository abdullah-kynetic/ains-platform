/**
 * Build-mode guard: the synthetic demo build (mocked data, no sign-in) must never be mistaken for a
 * real build. Run at `next build` time from next.config.ts, and directly by the production scripts.
 *
 *   KIEN_BUILD_TARGET=demo        the demo deploy (build:cloudflare, deploy:demo)
 *   KIEN_BUILD_TARGET=production  a real deploy (build:cloudflare:production, deploy:production)
 */
export function checkBuildMode(env) {
  const mocks = env.NEXT_PUBLIC_USE_MOCKS === "true";
  const target = env.KIEN_BUILD_TARGET ?? "";
  if (target === "production" && mocks)
    return "KIEN_BUILD_TARGET=production but NEXT_PUBLIC_USE_MOCKS=true. A real build must not use the demo (mock) data. Unset NEXT_PUBLIC_USE_MOCKS or set it to false.";
  if (target === "demo" && !mocks)
    return "KIEN_BUILD_TARGET=demo needs NEXT_PUBLIC_USE_MOCKS=true. A demo label on a real build (or the reverse) hides what is deployed.";
  if (mocks && target !== "demo")
    return "NEXT_PUBLIC_USE_MOCKS=true builds the synthetic demo. Use `npm run build:cloudflare` (demo) or set KIEN_BUILD_TARGET=demo on purpose.";
  if (target && target !== "demo" && target !== "production")
    return `Unknown KIEN_BUILD_TARGET "${target}". Use demo or production.`;
  return null;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const problem = checkBuildMode(process.env);
  if (problem) {
    console.error(`Build refused: ${problem}`);
    process.exit(1);
  }
}
