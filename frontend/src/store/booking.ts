/* ------------------------------------------------------------------ */
/*  Zustand store — single source of truth for the booking wizard      */
/* ------------------------------------------------------------------ */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Service, Provider, Slot, Booking } from "@/lib/api";

export type Step = 0 | 1 | 2 | 3; // Service → Provider/Date → Time → Confirm

/* ---- Toast system ---- */
export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

export interface BookingStore {
  /* ---- Wizard state ---- */
  step: Step;
  setStep: (s: Step) => void;
  nextStep: () => void;
  prevStep: () => void;

  /* ---- Selections ---- */
  selectedService: Service | null;
  selectService: (s: Service) => void;

  selectedProvider: Provider | null;
  selectProvider: (p: Provider) => void;

  selectedDate: string | null; // YYYY-MM-DD
  selectDate: (d: string) => void;

  selectedSlot: Slot | null;
  selectSlot: (s: Slot) => void;

  lockId: string | null;
  setLockId: (id: string | null) => void;

  lockExpiresAt: number | null; // epoch ms
  setLockExpiresAt: (ts: number | null) => void;

  /* ---- Customer (auto-fill for returning users) ---- */
  customerName: string;
  customerPhone: string;
  setCustomerName: (n: string) => void;
  setCustomerPhone: (p: string) => void;

  /* ---- Result ---- */
  confirmedBooking: Booking | null;
  setConfirmedBooking: (b: Booking | null) => void;

  /* ---- Loading / error ---- */
  loading: boolean;
  setLoading: (v: boolean) => void;
  error: string | null;
  setError: (e: string | null) => void;

  /* ---- Toasts ---- */
  toasts: Toast[];
  addToast: (type: ToastType, message: string) => void;
  removeToast: (id: string) => void;

  /* ---- Lock helpers ---- */
  lockExpired: boolean;
  setLockExpired: (v: boolean) => void;
  clearLock: () => void;

  /* ---- Reset ---- */
  reset: () => void;
}

const initialState = {
  step: 0 as Step,
  selectedService: null,
  selectedProvider: null,
  selectedDate: null,
  selectedSlot: null,
  lockId: null,
  lockExpiresAt: null,
  lockExpired: false,
  customerName: "",
  customerPhone: "",
  confirmedBooking: null,
  loading: false,
  error: null,
  toasts: [] as Toast[],
};

let toastCounter = 0;

export const useBookingStore = create<BookingStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setStep: (step) => set({ step }),
      nextStep: () => set((s) => ({ step: Math.min(s.step + 1, 3) as Step })),
      prevStep: () => set((s) => ({ step: Math.max(s.step - 1, 0) as Step })),

      selectService: (selectedService) =>
        set({ selectedService, selectedProvider: null, selectedDate: null, selectedSlot: null, lockId: null, lockExpiresAt: null, lockExpired: false, error: null }),
      selectProvider: (selectedProvider) =>
        set({ selectedProvider, selectedDate: null, selectedSlot: null, lockId: null, lockExpiresAt: null, lockExpired: false, error: null }),
      selectDate: (selectedDate) => set({ selectedDate, selectedSlot: null, lockId: null, lockExpiresAt: null, lockExpired: false, error: null }),
      selectSlot: (selectedSlot) => set({ selectedSlot, error: null }),

      setLockId: (lockId) => set({ lockId }),
      setLockExpiresAt: (lockExpiresAt) => set({ lockExpiresAt }),
      setCustomerName: (customerName) => set({ customerName }),
      setCustomerPhone: (customerPhone) => set({ customerPhone }),
      setConfirmedBooking: (confirmedBooking) => set({ confirmedBooking }),

      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),

      addToast: (type, message) => {
        const id = `toast-${++toastCounter}`;
        set((s) => ({ toasts: [...s.toasts, { id, type, message }] }));
        // Auto-dismiss after 5s
        setTimeout(() => get().removeToast(id), 5000);
      },
      removeToast: (id) =>
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

      setLockExpired: (lockExpired) => set({ lockExpired }),
      clearLock: () => set({ lockId: null, lockExpiresAt: null, lockExpired: false }),

      reset: () => set({ ...initialState, customerName: get().customerName, customerPhone: get().customerPhone }),
    }),
    {
      name: "booking-store",
      partialize: (state) => ({
        customerName: state.customerName,
        customerPhone: state.customerPhone,
      }),
    }
  )
);
