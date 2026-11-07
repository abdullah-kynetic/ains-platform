/** User-facing sign-in error text. Never reveals which of email or password was wrong. */
export type SignInFailure = {
  status: number;
  message: string;
  retryAfterSeconds?: number | null;
};

export function lockoutText(retryAfterSeconds?: number | null): string {
  if (!retryAfterSeconds || retryAfterSeconds <= 0)
    return "Too many failed attempts. Try again later.";
  const minutes = Math.ceil(retryAfterSeconds / 60);
  return minutes <= 1
    ? "Too many failed attempts. Try again in about a minute."
    : `Too many failed attempts. Try again in about ${minutes} minutes.`;
}

export function signInErrorText(failure: SignInFailure, step: "credentials" | "mfa"): string {
  if (failure.status === 429) return lockoutText(failure.retryAfterSeconds);
  if (failure.status === 503) return "Sign-in is temporarily unavailable. Try again shortly.";
  if (failure.status === 401 && step === "mfa") return "That code is not valid. Try again or use a recovery code.";
  if (failure.status === 401) return "Email or password is incorrect";
  return "Sign-in could not be completed. Try again.";
}
