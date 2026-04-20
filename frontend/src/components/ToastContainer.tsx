"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useBookingStore, type ToastType } from "@/store/booking";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={18} />,
  error: <XCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
};

const STYLES: Record<ToastType, string> = {
  success: "border-accent-green/30 text-accent-green",
  error: "border-accent-pink/30 text-accent-pink",
  warning: "border-accent-amber/30 text-accent-amber",
  info: "border-accent-cyan/30 text-accent-cyan",
};

export default function ToastContainer() {
  const toasts = useBookingStore((s) => s.toasts);
  const removeToast = useBookingStore((s) => s.removeToast);

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 80, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            className={cn(
              "glass-strong rounded-xl px-4 py-3 flex items-start gap-3 pointer-events-auto",
              "border",
              STYLES[toast.type],
            )}
          >
            <span className="mt-0.5 shrink-0">{ICONS[toast.type]}</span>
            <p className="text-sm text-white/90 flex-1">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-white/30 hover:text-white/60 transition shrink-0 mt-0.5 cursor-pointer"
            >
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
