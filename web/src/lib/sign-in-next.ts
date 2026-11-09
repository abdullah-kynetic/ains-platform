/** Accept only paths that remain on this portal's origin. */
export function sanitizeSignInNext(value: string | null | undefined): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\u0000-\u0020\u007f]/.test(value)
  )
    return "/";
  try {
    const base = "https://portal.example.invalid";
    const url = new URL(value, base);
    if (
      url.origin !== base ||
      !url.pathname.startsWith("/") ||
      url.pathname.startsWith("//")
    )
      return "/";
    return url.pathname + url.search + url.hash;
  } catch {
    return "/";
  }
}
