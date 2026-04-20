"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useBookingStore } from "@/store/booking";
import { cn } from "@/lib/utils";
import { api, friendlyError } from "@/lib/api";
import type { Provider, Slot } from "@/lib/api";
import { useEffect, useState, useCallback } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  Clock,
  User,
  Loader2,
} from "lucide-react";
import { format, addDays, isSameDay, parseISO, startOfToday } from "date-fns";

/* ------------------------------------------------------------------ */
/*  Date helpers                                                       */
/* ------------------------------------------------------------------ */

function buildWeek(start: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

/* ------------------------------------------------------------------ */
/*  Provider card                                                      */
/* ------------------------------------------------------------------ */

function ProviderCard({
  provider,
  isSelected,
  onSelect,
}: {
  provider: Provider;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      className={cn(
        "glass rounded-xl p-4 text-left transition-all duration-200 w-full cursor-pointer",
        isSelected
          ? "glow-cyan border-accent-cyan/40"
          : "hover:glass-strong"
      )}
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-dark-500 flex items-center justify-center text-accent-cyan">
          <User size={20} />
        </div>
        <div className="min-w-0">
          <p className="font-semibold truncate">{provider.name}</p>
          <p className="text-xs text-white/40">
            {provider.availability.length} day(s) available
          </p>
        </div>
      </div>
    </motion.button>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function DateTimeSelector() {
  const {
    selectedService,
    selectedProvider,
    selectProvider,
    selectedDate,
    selectDate,
    selectedSlot,
    selectSlot,
    nextStep,
    prevStep,
    setError,
  } = useBookingStore();

  const [providers, setProviders] = useState<Provider[]>([]);
  const [weekStart, setWeekStart] = useState(() => startOfToday());
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [providersError, setProvidersError] = useState<string | null>(null);

  const week = buildWeek(weekStart);

  /* ---- Fetch providers on service change ---- */
  useEffect(() => {
    if (!selectedService) return;
    setLoadingProviders(true);
    setProvidersError(null);
    api
      .getProviders(selectedService.id)
      .then((p) => {
        setProviders(p);
        if (p.length === 1) selectProvider(p[0]);
      })
      .catch((e) => {
        setProviders([]);
        setProvidersError(friendlyError(e));
      })
      .finally(() => setLoadingProviders(false));
  }, [selectedService]);

  /* ---- Fetch slots when provider + date selected ---- */
  const fetchSlots = useCallback(async () => {
    if (!selectedProvider || !selectedDate) return;
    setLoadingSlots(true);
    setSlotsError(null);
    try {
      const s = await api.getSlots(selectedProvider.id, selectedDate);
      setSlots(s);
    } catch (e) {
      // On poll failures, keep existing slots; only show error on empty
      if (slots.length === 0) {
        setSlotsError(friendlyError(e));
      }
    } finally {
      setLoadingSlots(false);
    }
  }, [selectedProvider, selectedDate]);

  useEffect(() => {
    fetchSlots();
    // Poll for real-time updates every 10s
    const timer = setInterval(fetchSlots, 10_000);
    return () => clearInterval(timer);
  }, [fetchSlots]);

  /* ---- Date pick ---- */
  const handleDateSelect = (d: Date) => {
    selectDate(format(d, "yyyy-MM-dd"));
  };

  const canContinue = selectedProvider && selectedDate && selectedSlot;

  return (
    <div className="max-w-5xl mx-auto px-4 space-y-8">
      {/* ---- Provider list ---- */}
      <section>
        <h2 className="text-lg font-semibold text-white/80 mb-4 flex items-center gap-2">
          <User size={18} className="text-accent-cyan" />
          Choose a provider
        </h2>

        {loadingProviders ? (
          <Loader size="md" />
        ) : providersError ? (
          <div className="glass rounded-xl p-6 text-center text-accent-pink text-sm">{providersError}</div>
        ) : (
          <motion.div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
            initial="hidden"
            animate="show"
            variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}
          >
            {providers.map((p) => (
              <motion.div
                key={p.id}
                variants={{ hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }}
              >
                <ProviderCard
                  provider={p}
                  isSelected={selectedProvider?.id === p.id}
                  onSelect={() => selectProvider(p)}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </section>

      {/* ---- Date calendar strip ---- */}
      <section>
        <h2 className="text-lg font-semibold text-white/80 mb-4 flex items-center gap-2">
          <Calendar size={18} className="text-accent-purple" />
          Pick a date
        </h2>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekStart((s) => addDays(s, -7))}
            className="p-2 rounded-lg glass hover:glass-strong transition"
          >
            <ChevronLeft size={18} />
          </button>

          <div className="flex-1 grid grid-cols-7 gap-2">
            {week.map((d) => {
              const dateStr = format(d, "yyyy-MM-dd");
              const isToday = isSameDay(d, new Date());
              const isActive = selectedDate === dateStr;
              const isPast = d < startOfToday();

              return (
                <motion.button
                  key={dateStr}
                  whileHover={!isPast ? { scale: 1.08 } : {}}
                  whileTap={!isPast ? { scale: 0.95 } : {}}
                  disabled={isPast}
                  onClick={() => handleDateSelect(d)}
                  className={cn(
                    "flex flex-col items-center py-3 rounded-xl transition-all duration-200",
                    isPast && "opacity-30 cursor-not-allowed",
                    isActive
                      ? "glass glow-purple border-accent-purple/40 text-accent-purple"
                      : "glass hover:glass-strong cursor-pointer",
                    isToday && !isActive && "border-accent-cyan/20"
                  )}
                >
                  <span className="text-[10px] uppercase tracking-wider text-white/40">
                    {format(d, "EEE")}
                  </span>
                  <span className="text-lg font-bold">{format(d, "d")}</span>
                  <span className="text-[10px] text-white/30">{format(d, "MMM")}</span>
                </motion.button>
              );
            })}
          </div>

          <button
            onClick={() => setWeekStart((s) => addDays(s, 7))}
            className="p-2 rounded-lg glass hover:glass-strong transition"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </section>

      {/* ---- Time slots grid ---- */}
      <AnimatePresence mode="wait">
        {selectedProvider && selectedDate && (
          <motion.section
            key={selectedDate}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <h2 className="text-lg font-semibold text-white/80 mb-4 flex items-center gap-2">
              <Clock size={18} className="text-accent-pink" />
              Available times
            </h2>

            {loadingSlots ? (
              <Loader size="md" />
            ) : slotsError ? (
              <div className="glass rounded-xl p-8 text-center text-accent-pink text-sm">
                {slotsError}
              </div>
            ) : slots.length === 0 ? (
              <div className="glass rounded-xl p-8 text-center text-white/40">
                No slots available for this date. Try another day.
              </div>
            ) : (
              <motion.div
                className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2"
                initial="hidden"
                animate="show"
                variants={{ hidden: {}, show: { transition: { staggerChildren: 0.02 } } }}
              >
                {slots.map((slot) => {
                  const isSelected = selectedSlot?.id === slot.id;
                  const isLocked = slot.status === "locked";
                  const isBooked = slot.status === "booked";
                  const disabled = isLocked || isBooked;

                  return (
                    <motion.button
                      key={slot.id}
                      variants={{
                        hidden: { opacity: 0, scale: 0.8 },
                        show: { opacity: 1, scale: 1 },
                      }}
                      whileHover={!disabled ? { scale: 1.1, y: -2 } : {}}
                      whileTap={!disabled ? { scale: 0.95 } : {}}
                      disabled={disabled}
                      onClick={() => selectSlot(slot)}
                      className={cn(
                        "py-3 px-2 rounded-xl text-sm font-semibold transition-all duration-200 relative overflow-hidden",
                        disabled
                          ? "bg-dark-700/60 text-white/20 cursor-not-allowed line-through"
                          : isSelected
                          ? "glass glow-cyan border-accent-cyan/50 text-accent-cyan"
                          : "glass hover:glass-strong cursor-pointer text-white/70 hover:text-white"
                      )}
                    >
                      {slot.time}
                      {isLocked && (
                        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent-amber animate-pulse" />
                      )}
                      {isBooked && (
                        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent-pink" />
                      )}
                    </motion.button>
                  );
                })}
              </motion.div>
            )}

            {/* Legend */}
            <div className="flex items-center gap-6 mt-4 text-xs text-white/40">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-accent-cyan" /> Selected
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-accent-amber animate-pulse" /> Locked
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-accent-pink" /> Booked
              </span>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* ---- Navigation ---- */}
      <div className="flex justify-between pt-4">
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          onClick={prevStep}
          className="glass rounded-xl px-6 py-3 text-sm font-semibold hover:glass-strong transition cursor-pointer"
        >
          ← Back
        </motion.button>

        <motion.button
          whileHover={canContinue ? { scale: 1.04 } : {}}
          whileTap={canContinue ? { scale: 0.96 } : {}}
          disabled={!canContinue}
          onClick={nextStep}
          className={cn(
            "rounded-xl px-6 py-3 text-sm font-bold transition-all duration-300 cursor-pointer",
            canContinue
              ? "bg-gradient-to-r from-accent-cyan to-accent-purple text-dark-900 glow-cyan"
              : "bg-dark-700 text-white/30 cursor-not-allowed"
          )}
        >
          Continue →
        </motion.button>
      </div>
    </div>
  );
}

/* Simple spinner */
function Loader({ size = "md" }: { size?: "sm" | "md" }) {
  const dim = size === "sm" ? "w-6 h-6" : "w-10 h-10";
  return (
    <div className="flex items-center justify-center py-12">
      <motion.div
        className={cn(dim, "border-2 border-accent-cyan border-t-transparent rounded-full")}
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
      />
    </div>
  );
}
