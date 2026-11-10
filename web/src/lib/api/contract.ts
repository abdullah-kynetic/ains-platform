import { apiRequest, ApiError } from "../api";

/** A contract exists in the web, but its server route has not landed yet. */
export class NotAvailableError extends Error {
  constructor() {
    super("Not available yet");
    this.name = "NotAvailableError";
  }
}

/** Preserve authentication, ownership and validation errors from implemented routes. */
export async function contractRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await apiRequest<T>(path, init);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && error.message === "Not Found") {
      throw new NotAvailableError();
    }
    throw error;
  }
}
