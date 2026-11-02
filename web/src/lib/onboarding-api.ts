import { apiRequest, AUTH_REMOVED, USE_MOCKS, clientMocksEnabled } from "./api";
export type OnboardingState = {
  state: "pending" | "completed" | "skipped";
  flow: "client" | "auditor";
};
function key(role: string) {
  return `kien-synthetic-onboarding-${role}`;
}
export async function getOnboarding(
  role: "client" | "auditor",
): Promise<OnboardingState> {
  if ((!AUTH_REMOVED || USE_MOCKS) && !clientMocksEnabled()) return apiRequest("/auth/onboarding");
  // Static synthetic demos have no first sign-in; opt in when exercising the walkthrough.
  return {
    flow: role,
    state:
      localStorage.getItem("kien-synthetic-onboarding-enabled") === "1"
        ? ((localStorage.getItem(key(role)) as OnboardingState["state"]) ??
          "pending")
        : "completed",
  };
}
export async function finishOnboarding(
  role: "client" | "auditor",
  action: "completed" | "skipped",
): Promise<OnboardingState> {
  if ((!AUTH_REMOVED || USE_MOCKS) && !clientMocksEnabled())
    return apiRequest("/auth/onboarding", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  localStorage.setItem(key(role), action);
  return { flow: role, state: action };
}
