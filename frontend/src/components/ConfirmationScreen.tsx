"use client";

import { motion } from "framer-motion";
import { useBookingStore } from "@/store/booking";
import { api, friendlyError } from "@/lib/api";
import {
  CheckCircle2,
  Calendar,
  Clock,
  User,
  Phone,
  Copy,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { useState } from "react";

export default function ConfirmationScreen() {
  const { confirmedBooking, selectedService, selectedProvider, customerName, customerPhone, reset, addToast } =
    useBookingStore();
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  if (!confirmedBooking) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(confirmedBooking.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-lg mx-auto px-4 flex flex-col items-center">
      {/* ---- Animated check ---- */}
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.1 }}
        className="w-24 h-24 rounded-full bg-accent-green/10 flex items-center justify-center mb-6 glow-green"
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <CheckCircle2 size={48} className="text-accent-green" />
        </motion.div>
      </motion.div>

      {/* ---- Title ---- */}
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="text-2xl font-bold mb-1 text-center"
      >
        Booking Confirmed!
      </motion.h1>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-white/40 text-sm mb-8 text-center"
      >
        You&apos;re all set. Here are your booking details.
      </motion.p>

      {/* ---- Details card ---- */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="w-full glass rounded-2xl overflow-hidden mb-6"
      >
        <div className="h-1.5 bg-gradient-to-r from-accent-green via-accent-cyan to-accent-purple" />

        <div className="p-6 space-y-4">
          {/* Booking ID */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/40">Booking ID</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs font-mono text-accent-cyan hover:text-accent-cyan/80 transition cursor-pointer"
            >
              {confirmedBooking.id.slice(0, 12)}…
              {copied ? (
                <CheckCircle2 size={12} className="text-accent-green" />
              ) : (
                <Copy size={12} />
              )}
            </button>
          </div>

          <div className="h-px bg-white/5" />

          <DetailRow icon={<User size={16} />} label="Service" value={selectedService?.name ?? "—"} />
          <DetailRow icon={<User size={16} />} label="Provider" value={selectedProvider?.name ?? "—"} />
          <DetailRow icon={<Calendar size={16} />} label="Date" value={confirmedBooking.date} />
          <DetailRow icon={<Clock size={16} />} label="Time" value={confirmedBooking.time} />
          <DetailRow icon={<User size={16} />} label="Name" value={customerName} />
          <DetailRow icon={<Phone size={16} />} label="Phone" value={customerPhone} />

          <div className="h-px bg-white/5" />

          <div className="flex items-center justify-between">
            <span className="text-xs text-white/40">Status</span>
            <span className="text-xs font-bold text-accent-green bg-accent-green/10 px-3 py-1 rounded-full uppercase tracking-wider">
              {confirmedBooking.status}
            </span>
          </div>
        </div>
      </motion.div>

      {/* ---- Particle burst (decorative) ---- */}
      <Particles />

      {/* ---- Cancel booking ---- */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9 }}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        disabled={cancelling || confirmedBooking.status === "cancelled"}
        onClick={async () => {
          setCancelling(true);
          try {
            await api.cancelBooking(confirmedBooking.id);
            addToast("success", "Booking cancelled successfully.");
            reset();
          } catch (e) {
            addToast("error", friendlyError(e));
          } finally {
            setCancelling(false);
          }
        }}
        className="glass rounded-xl px-8 py-3 text-sm font-semibold hover:glass-strong transition flex items-center gap-2 cursor-pointer text-accent-pink border-accent-pink/20"
      >
        <XCircle size={16} /> {cancelling ? "Cancelling…" : "Cancel Booking"}
      </motion.button>

      {/* ---- New booking ---- */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        onClick={reset}
        className="glass rounded-xl px-8 py-3 text-sm font-semibold hover:glass-strong transition flex items-center gap-2 cursor-pointer"
      >
        <RotateCcw size={16} /> Book Another Appointment
      </motion.button>
    </div>
  );
}

function DetailRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-accent-cyan/50">{icon}</span>
      <span className="text-xs text-white/40 w-16">{label}</span>
      <span className="text-sm font-medium text-white/90">{value}</span>
    </div>
  );
}

/* Decorative confetti-like particles */
function Particles() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-50">
      {Array.from({ length: 20 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1.5 h-1.5 rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: "-5%",
            backgroundColor: ["#00e5ff", "#b14aed", "#ff2d87", "#39ff14", "#ffab00"][
              i % 5
            ],
          }}
          initial={{ opacity: 1, y: 0 }}
          animate={{
            y: typeof window !== "undefined" ? window.innerHeight * 1.2 : 800,
            opacity: 0,
            rotate: Math.random() * 360,
          }}
          transition={{
            duration: 2 + Math.random() * 2,
            delay: 0.5 + Math.random() * 0.5,
            ease: "easeIn",
          }}
        />
      ))}
    </div>
  );
}
