"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useBookingStore } from "@/store/booking";
import { Check } from "lucide-react";

const STEPS = ["Service", "Date & Provider", "Time Slot", "Confirm"] as const;

export default function ProgressBar() {
  const step = useBookingStore((s) => s.step);

  return (
    <div className="w-full max-w-2xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between relative">
        {/* Connecting line (background) */}
        <div className="absolute top-5 left-[10%] right-[10%] h-[2px] bg-dark-600 z-0" />

        {/* Connecting line (active fill) */}
        <motion.div
          className="absolute top-5 left-[10%] h-[2px] bg-gradient-to-r from-accent-cyan via-accent-purple to-accent-pink z-[1]"
          initial={{ width: "0%" }}
          animate={{ width: `${(step / (STEPS.length - 1)) * 80}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />

        {STEPS.map((label, i) => {
          const isActive = i === step;
          const isCompleted = i < step;

          return (
            <div key={label} className="flex flex-col items-center gap-2 z-10">
              <motion.div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors duration-300",
                  isCompleted
                    ? "bg-accent-cyan text-dark-900"
                    : isActive
                    ? "glass glow-cyan text-accent-cyan border-accent-cyan/40"
                    : "bg-dark-700 text-white/40 border border-dark-500"
                )}
                animate={isActive ? { scale: [1, 1.12, 1] } : { scale: 1 }}
                transition={isActive ? { repeat: Infinity, duration: 2, ease: "easeInOut" } : {}}
              >
                {isCompleted ? <Check size={18} /> : i + 1}
              </motion.div>
              <span
                className={cn(
                  "text-xs font-medium whitespace-nowrap",
                  isActive
                    ? "text-accent-cyan text-glow-cyan"
                    : isCompleted
                    ? "text-white/80"
                    : "text-white/30"
                )}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
