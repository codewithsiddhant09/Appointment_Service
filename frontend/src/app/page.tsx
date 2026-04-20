"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useBookingStore, type Step } from "@/store/booking";
import ProgressBar from "@/components/ProgressBar";
import ServiceSelection from "@/components/ServiceSelection";
import DateTimeSelector from "@/components/DateTimeSelector";
import BookingSummary from "@/components/BookingSummary";
import ConfirmationScreen from "@/components/ConfirmationScreen";
import ToastContainer from "@/components/ToastContainer";
import { CalendarCheck } from "lucide-react";

const STEP_TITLES: Record<Step, string> = {
  0: "Choose a Service",
  1: "Select Provider & Date",
  2: "Confirm Your Booking",
  3: "All Done!",
};

const variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 60 : -60,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction > 0 ? -60 : 60,
    opacity: 0,
  }),
};

export default function HomePage() {
  const step = useBookingStore((s) => s.step);

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* ------------------------------------------------------------------ */}
      {/*  Background decorations                                             */}
      {/* ------------------------------------------------------------------ */}
      <div className="fixed inset-0 -z-10">
        {/* Gradient orbs */}
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-accent-cyan/[0.04] blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-accent-purple/[0.05] blur-[120px]" />
        <div className="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-accent-pink/[0.03] blur-[100px]" />

        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
            backgroundSize: "64px 64px",
          }}
        />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/*  Header                                                             */}
      {/* ------------------------------------------------------------------ */}
      <header className="w-full pt-8 pb-2">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center">
            <CalendarCheck size={20} className="text-dark-900" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">AppointmentAgent</h1>
            <p className="text-xs text-white/30">Smart booking, zero hassle</p>
          </div>
        </div>
      </header>

      {/* ---- Progress ---- */}
      <ProgressBar />

      {/* ---- Step title ---- */}
      <div className="text-center mb-8">
        <AnimatePresence mode="wait">
          <motion.h2
            key={step}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="text-2xl md:text-3xl font-extrabold bg-gradient-to-r from-white via-white/90 to-white/60 bg-clip-text text-transparent"
          >
            {STEP_TITLES[step]}
          </motion.h2>
        </AnimatePresence>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/*  Step content                                                       */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex-1 pb-16">
        <AnimatePresence mode="wait" custom={step}>
          <motion.div
            key={step}
            custom={step}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.35, ease: "easeInOut" }}
          >
            {step === 0 && <ServiceSelection />}
            {step === 1 && <DateTimeSelector />}
            {step === 2 && <BookingSummary />}
            {step === 3 && <ConfirmationScreen />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* ---- Toast notifications ---- */}
      <ToastContainer />

      {/* ---- Footer ---- */}
      <footer className="text-center py-4 text-xs text-white/15">
        © 2026 AppointmentAgent — Built with Next.js, FastAPI &amp; Redis
      </footer>
    </div>
  );
}
