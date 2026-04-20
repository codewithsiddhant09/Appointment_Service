/* ------------------------------------------------------------------ */
/*  API client — production-ready with retry, timeout, error mapping   */
/* ------------------------------------------------------------------ */

const BASE = "/api/v1";
const DEFAULT_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 3;

/* ---- Error class with status code ---- */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/* ---- User-friendly error mapping by HTTP status ---- */

export function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 409:
        return "This slot was just booked by someone else. Please pick another.";
      case 403:
        return "This slot was not reserved by you. Please reserve it first.";
      case 410:
        return "Your reservation expired. Please reserve the slot again.";
      case 422:
        return "Please check your input and try again.";
      case 423:
        return "This slot is currently held by another user. Try again shortly.";
      case 404:
        return "The requested resource was not found.";
      case 500:
        return "Something went wrong on our end. Please try again.";
      default:
        return err.message;
    }
  }
  if (err instanceof DOMException && err.name === "AbortError") {
    return "Request timed out. Please check your connection and try again.";
  }
  return "An unexpected error occurred. Please try again.";
}

/* ---- Core request with timeout ---- */

async function request<T>(
  path: string,
  opts?: RequestInit & { timeout?: number },
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT_MS, ...fetchOpts } = opts ?? {};

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...fetchOpts.headers },
      signal: controller.signal,
      ...fetchOpts,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? res.statusText);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/* ---- Request with exponential-backoff retry ---- */

async function requestWithRetry<T>(
  path: string,
  opts?: RequestInit & { timeout?: number },
  retries = MAX_RETRIES,
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await request<T>(path, opts);
    } catch (err) {
      lastError = err;

      // Don't retry client errors (4xx) except 408/429
      if (
        err instanceof ApiError &&
        err.status >= 400 &&
        err.status < 500 &&
        err.status !== 408 &&
        err.status !== 429
      ) {
        throw err;
      }

      // Last attempt — throw
      if (attempt === retries - 1) break;

      // Exponential backoff: 500ms, 1s, 2s + jitter
      const delay = Math.min(500 * Math.pow(2, attempt), 4000);
      const jitter = Math.random() * 200;
      await new Promise((r) => setTimeout(r, delay + jitter));
    }
  }
  throw lastError;
}

/* ---- In-flight request deduplication for GET calls ---- */

const inflightGets = new Map<string, Promise<any>>();

function deduplicatedGet<T>(path: string): Promise<T> {
  const existing = inflightGets.get(path);
  if (existing) return existing;

  const promise = requestWithRetry<T>(path).finally(() => {
    inflightGets.delete(path);
  });
  inflightGets.set(path, promise);
  return promise;
}

/* ---- Types ---- */

export interface Service {
  id: string;
  name: string;
  category: "doctor" | "lawyer" | "salon";
}

export interface Provider {
  id: string;
  name: string;
  service_id: string;
  availability: DayAvailability[];
}

export interface DayAvailability {
  day: string;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
}

export interface Slot {
  id: string;
  provider_id: string;
  date: string;
  time: string;
  status: "available" | "locked" | "booked";
}

export interface LockResult {
  lock_id: string;
  provider_id: string;
  date: string;
  time: string;
  expires_at: string;
}

export interface Booking {
  id: string;
  customer_id: string;
  provider_id: string;
  date: string;
  time: string;
  status: string;
  created_at: string;
  updated_at: string;
}

/* ---- Endpoints ---- */

export const api = {
  /* ---- Read (deduplicated + retried) ---- */

  getServices: () => deduplicatedGet<Service[]>("/services"),

  getProviders: (serviceId?: string) =>
    deduplicatedGet<Provider[]>(
      serviceId ? `/providers?service_id=${serviceId}` : "/providers",
    ),

  getSlots: (providerId: string, date: string) =>
    deduplicatedGet<Slot[]>(
      `/slots?provider_id=${providerId}&date=${date}`,
    ),

  /* ---- Write (retried where safe, no dedup) ---- */

  generateSlots: (
    providerId: string,
    date: string,
    startTime = "09:00",
    endTime = "17:00",
    duration = 30,
  ) =>
    requestWithRetry<{ created: number }>(
      `/slots/generate?provider_id=${providerId}&date=${date}&start_time=${startTime}&end_time=${endTime}&duration_minutes=${duration}`,
      { method: "POST" },
    ),

  lockSlot: (body: {
    provider_id: string;
    date: string;
    time: string;
    customer_phone: string;
  }) =>
    request<LockResult>("/slots/lock", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  confirmBooking: (body: {
    slot_id: string;
    customer_id: string;      // customer phone — matches the identifier used when locking
    customer_name: string;
    provider_id: string;
    date: string;
    time: string;
  }) =>
    request<Booking>("/bookings", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  cancelBooking: (bookingId: string) =>
    request<Booking>(`/bookings/${encodeURIComponent(bookingId)}/cancel`, {
      method: "PATCH",
    }),

  rescheduleBooking: (
    bookingId: string,
    body: { new_date: string; new_time: string; lock_id: string },
  ) =>
    request<Booking>(
      `/bookings/${encodeURIComponent(bookingId)}/reschedule`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),
};
