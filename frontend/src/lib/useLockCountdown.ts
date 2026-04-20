import { useEffect, useRef, useState } from "react";
import { useBookingStore } from "@/store/booking";

/**
 * Returns the seconds remaining on the current slot lock.
 * Returns null when no lock is active.
 * Sets lockExpired=true in the store when TTL hits 0 (keeps lockId intact
 * so the UI knows which state to render: expired vs. no-lock).
 */
export function useLockCountdown(): number | null {
  const lockExpiresAt = useBookingStore((s) => s.lockExpiresAt);
  const lockId = useBookingStore((s) => s.lockId);
  const setLockExpired = useBookingStore((s) => s.setLockExpired);
  const addToast = useBookingStore((s) => s.addToast);
  const [remaining, setRemaining] = useState<number | null>(null);
  const expiredFired = useRef(false);

  useEffect(() => {
    // Reset the fired flag when a new lock is acquired
    expiredFired.current = false;
  }, [lockId]);

  useEffect(() => {
    if (!lockExpiresAt || !lockId) {
      setRemaining(null);
      return;
    }

    const tick = () => {
      const secs = Math.max(0, Math.floor((lockExpiresAt - Date.now()) / 1000));
      setRemaining(secs);

      if (secs <= 0 && !expiredFired.current) {
        expiredFired.current = true;
        setLockExpired(true);
        addToast("warning", "Your slot reservation expired. Please reserve again.");
      }
    };

    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [lockExpiresAt, lockId, setLockExpired, addToast]);

  return remaining;
}
