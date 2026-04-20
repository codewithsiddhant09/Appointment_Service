"use client";

import { motion } from "framer-motion";
import { useBookingStore } from "@/store/booking";
import { cn } from "@/lib/utils";
import { api, ApiError, friendlyError } from "@/lib/api";
import { useLockCountdown } from "@/lib/useLockCountdown";
import {
  Calendar,
  Clock,
  User,
  Phone,
  Shield,
  ChevronLeft,
  Timer,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import VoiceButton from "./VoiceButton";

export default function BookingSummary() {
  const {
    selectedService,
    selectedProvider,
    selectedDate,
    selectedSlot,
    lockId,
    setLockId,
    setLockExpiresAt,
    lockExpired,
    setLockExpired,
    clearLock,
    customerName,
    customerPhone,
    setCustomerName,
    setCustomerPhone,
    setConfirmedBooking,
    nextStep,
    prevStep,
    loading,
    setLoading,
    error,
    setError,
    addToast,
  } = useBookingStore();

  const [locking, setLocking] = useState(false);
  const countdown = useLockCountdown();

  const lockActive = lockId !== null && !lockExpired && countdown !== null && countdown > 0;

  const canLock =
    selectedProvider &&
    selectedDate &&
    selectedSlot &&
    customerPhone.length >= 7 &&
    !lockActive &&
    !locking;

  const canConfirm =
    lockActive && lockId && customerName.trim().length > 0 && customerPhone.length >= 7;

  /* ---- Lock the slot ---- */
  const handleLock = async () => {
    if (!selectedProvider || !selectedDate || !selectedSlot) return;
    setLocking(true);
    setError(null);
    try {
      const res = await api.lockSlot({
        provider_id: selectedProvider.id,
        date: selectedDate,
        time: selectedSlot.time,
        customer_phone: customerPhone,
      });
      setLockId(res.lock_id);
      setLockExpiresAt(new Date(res.expires_at).getTime());
      setLockExpired(false);
      addToast("success", "Slot reserved! Complete your booking before the timer runs out.");
    } catch (e: unknown) {
      const msg = friendlyError(e);
      setError(msg);
      // If slot was locked by someone else, suggest different slot
      if (e instanceof ApiError && e.status === 423) {
        addToast("warning", "Try a different time — this one is being held by another user.");
      }
    } finally {
      setLocking(false);
    }
  };

  /* ---- Re-lock after expiry ---- */
  const handleRelock = () => {
    clearLock();
    setError(null);
    handleLock();
  };

  /* ---- Confirm booking ---- */
  const handleConfirmBooking = async () => {
    if (!canConfirm || !selectedProvider || !selectedDate || !selectedSlot) return;
    setLoading(true);
    setError(null);
    try {
      const booking = await api.confirmBooking({
        slot_id: selectedSlot.id,
        customer_id: customerPhone,
        customer_name: customerName,
        provider_id: selectedProvider.id,
        date: selectedDate,
        time: selectedSlot.time,
      });
      setConfirmedBooking(booking);
      addToast("success", "Booking confirmed! Redirecting to your confirmation...");
      nextStep();
    } catch (e: unknown) {
      const msg = friendlyError(e);
      setError(msg);

      if (e instanceof ApiError) {
        if (e.status === 410) {
          // Slot expired — let user re-lock
          clearLock();
          addToast("warning", "Slot expired. Hit \u2018Reserve\u2019 to try again.");
        } else if (e.status === 409) {
          // Double-booking — go back to slot selection
          clearLock();
          addToast("error", "Slot conflict. Please choose a different time.");
        } else if (e.status === 403) {
          // Slot locked by someone else
          clearLock();
          addToast("error", "This slot was not reserved by you. Please reserve again.");
        }
      }
    } finally {
      setLoading(false);
    }
  };

  /* ---- Voice transcript handler ---- */
  const handleVoiceResult = (transcript: string) => {
    const digitsOnly = transcript.replace(/\D/g, "");
    if (digitsOnly.length >= 7) {
      setCustomerPhone(digitsOnly);
      addToast("info", `Phone set: ${digitsOnly}`);
    } else {
      setCustomerName(transcript);
      addToast("info", `Name set: ${transcript}`);
    }
  };

  /* ---- Format countdown ---- */
  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="max-w-xl mx-auto px-4 space-y-6">
      {/* ---- Summary card ---- */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl overflow-hidden"
      >
        <div className="h-1.5 bg-gradient-to-r from-accent-cyan via-accent-purple to-accent-pink" />

        <div className="p-6 space-y-5">
          <h2 className="text-xl font-bold text-glow-cyan text-accent-cyan">
            Booking Summary
          </h2>

          <div className="space-y-3">
            <SummaryRow icon={<Shield size={16} />} label="Service" value={selectedService?.name} />
            <SummaryRow icon={<User size={16} />} label="Provider" value={selectedProvider?.name} />
            <SummaryRow icon={<Calendar size={16} />} label="Date" value={selectedDate ?? "—"} />
            <SummaryRow icon={<Clock size={16} />} label="Time" value={selectedSlot?.time ?? "—"} />
          </div>
        </div>
      </motion.div>

      {/* ---- Customer form ---- */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl p-6 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white/80">Your Details</h3>
          <VoiceButton onResult={handleVoiceResult} />
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-white/40 mb-1 block">Full Name</label>
            <input
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="John Doe"
              className="w-full glass rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/40 placeholder:text-white/20 bg-transparent"
            />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Phone Number</label>
            <div className="relative">
              <Phone size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+1 555 000 0000"
                className="w-full glass rounded-xl pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/40 placeholder:text-white/20 bg-transparent"
              />
            </div>
          </div>
        </div>

        {customerName && customerPhone && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-accent-green/70"
          >
            ✓ Your details are saved for next time
          </motion.p>
        )}
      </motion.div>

      {/* ---- Error ---- */}
      {error && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-xl bg-accent-pink/10 border border-accent-pink/30 px-4 py-3 text-sm text-accent-pink"
        >
          {error}
        </motion.div>
      )}

      {/* ---- Lock countdown timer ---- */}
      {lockActive && countdown !== null && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={cn(
            "rounded-xl px-4 py-3 text-sm text-center flex items-center justify-center gap-2",
            countdown > 60
              ? "bg-accent-green/10 border border-accent-green/30 text-accent-green"
              : countdown > 30
              ? "bg-accent-amber/10 border border-accent-amber/30 text-accent-amber"
              : "bg-accent-pink/10 border border-accent-pink/30 text-accent-pink animate-pulse"
          )}
        >
          <Timer size={16} />
          Slot reserved — {formatCountdown(countdown)} remaining
        </motion.div>
      )}

      {/* ---- Lock expired — offer re-lock ---- */}
      {lockExpired && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-xl bg-accent-amber/10 border border-accent-amber/30 px-4 py-3 text-sm text-accent-amber text-center space-y-2"
        >
          <p>Your reservation expired.</p>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleRelock}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg glass hover:glass-strong transition text-accent-cyan text-xs font-semibold cursor-pointer"
          >
            <RefreshCw size={14} /> Reserve Again
          </motion.button>
        </motion.div>
      )}

      {/* ---- Lock & Confirm buttons ---- */}
      <div className="space-y-3">
        {!lockActive && !lockExpired && (
          <motion.button
            whileHover={canLock ? { scale: 1.02 } : {}}
            whileTap={canLock ? { scale: 0.98 } : {}}
            disabled={!canLock || locking}
            onClick={handleLock}
            className={cn(
              "w-full rounded-xl py-3.5 text-sm font-bold transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer",
              canLock
                ? "glass glow-purple text-accent-purple border-accent-purple/30 hover:glass-strong"
                : "bg-dark-700 text-white/30 cursor-not-allowed"
            )}
          >
            {locking ? (
              <>
                <motion.div
                  className="w-4 h-4 border-2 border-accent-purple border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.6, ease: "linear" }}
                />
                Reserving slot…
              </>
            ) : (
              <>
                <Shield size={16} /> Reserve Slot (5 min hold)
              </>
            )}
          </motion.button>
        )}

        <motion.button
          whileHover={canConfirm ? { scale: 1.02 } : {}}
          whileTap={canConfirm ? { scale: 0.98 } : {}}
          disabled={!canConfirm || loading}
          onClick={handleConfirmBooking}
          className={cn(
            "w-full rounded-xl py-3.5 text-sm font-bold transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer",
            canConfirm
              ? "bg-gradient-to-r from-accent-cyan to-accent-purple text-dark-900 glow-cyan"
              : "bg-dark-700 text-white/30 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <motion.div
                className="w-4 h-4 border-2 border-dark-900 border-t-transparent rounded-full"
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 0.6, ease: "linear" }}
              />
              Confirming…
            </>
          ) : (
            "Confirm Booking"
          )}
        </motion.button>
      </div>

      {/* ---- Back ---- */}
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={prevStep}
        className="glass rounded-xl px-6 py-3 text-sm font-semibold hover:glass-strong transition flex items-center gap-1 cursor-pointer"
      >
        <ChevronLeft size={16} /> Back
      </motion.button>
    </div>
  );
}

function SummaryRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value?: string | null;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-accent-cyan/60">{icon}</span>
      <span className="text-xs text-white/40 w-16">{label}</span>
      <span className="text-sm font-medium text-white/90">{value ?? "—"}</span>
    </div>
  );
}
