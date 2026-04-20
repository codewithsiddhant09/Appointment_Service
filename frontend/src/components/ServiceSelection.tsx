"use client";

import { motion } from "framer-motion";
import { useBookingStore } from "@/store/booking";
import { cn } from "@/lib/utils";
import {
  Stethoscope,
  Scale,
  Scissors,
  ChevronRight,
} from "lucide-react";
import type { Service } from "@/lib/api";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const ICONS: Record<string, React.ReactNode> = {
  doctor: <Stethoscope size={36} />,
  lawyer: <Scale size={36} />,
  salon: <Scissors size={36} />,
};

const GLOWS: Record<string, string> = {
  doctor: "glow-cyan",
  lawyer: "glow-purple",
  salon: "glow-pink",
};

const ACCENT_TEXT: Record<string, string> = {
  doctor: "text-accent-cyan",
  lawyer: "text-accent-purple",
  salon: "text-accent-pink",
};

const ACCENT_BORDER: Record<string, string> = {
  doctor: "border-accent-cyan/30",
  lawyer: "border-accent-purple/30",
  salon: "border-accent-pink/30",
};

const DESCRIPTIONS: Record<string, string> = {
  doctor: "Consult with top physicians — general checkups, specialists & more.",
  lawyer: "Legal advice from experienced attorneys for any matter.",
  salon: "Premium haircuts, styling & beauty treatments.",
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const card = {
  hidden: { opacity: 0, y: 40, rotateX: 8 },
  show: { opacity: 1, y: 0, rotateX: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export default function ServiceSelection() {
  const { selectService, nextStep, selectedService } = useBookingStore();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getServices()
      .then(setServices)
      .catch(() =>
        setServices([
          { id: "svc_doctor", name: "Doctor Consultation", category: "doctor" },
          { id: "svc_lawyer", name: "Legal Advice", category: "lawyer" },
          { id: "svc_salon", name: "Hair Salon", category: "salon" },
        ])
      )
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = (svc: Service) => {
    selectService(svc);
    nextStep();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <motion.div
          className="w-10 h-10 border-2 border-accent-cyan border-t-transparent rounded-full"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
        />
      </div>
    );
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto px-4"
    >
      {services.map((svc) => {
        const cat = svc.category;
        const isSelected = selectedService?.id === svc.id;
        return (
          <motion.button
            key={svc.id}
            variants={card}
            whileHover={{ y: -6, scale: 1.03, transition: { duration: 0.2 } }}
            whileTap={{ scale: 0.97 }}
            onClick={() => handleSelect(svc)}
            className={cn(
              "group relative glass rounded-2xl p-8 text-left transition-all duration-300 cursor-pointer",
              "hover:glass-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan/50",
              isSelected && [GLOWS[cat], ACCENT_BORDER[cat]],
              "gradient-border"
            )}
          >
            {/* Icon */}
            <div
              className={cn(
                "w-16 h-16 rounded-xl flex items-center justify-center mb-5 transition-colors duration-300",
                "bg-dark-600 group-hover:bg-dark-500",
                ACCENT_TEXT[cat]
              )}
            >
              {ICONS[cat]}
            </div>

            {/* Title */}
            <h3
              className={cn(
                "text-xl font-bold mb-2 transition-colors duration-300",
                "group-hover:" + ACCENT_TEXT[cat].replace("text-", "text-")
              )}
            >
              {svc.name}
            </h3>

            {/* Description */}
            <p className="text-sm text-white/50 mb-6 leading-relaxed">
              {DESCRIPTIONS[cat] ?? "Book your next appointment."}
            </p>

            {/* CTA */}
            <span
              className={cn(
                "inline-flex items-center gap-1 text-sm font-semibold transition-colors",
                ACCENT_TEXT[cat]
              )}
            >
              Book now
              <ChevronRight
                size={16}
                className="group-hover:translate-x-1 transition-transform"
              />
            </span>

            {/* Decorative gradient blob */}
            <div
              className={cn(
                "absolute -bottom-8 -right-8 w-32 h-32 rounded-full blur-3xl opacity-0 group-hover:opacity-20 transition-opacity duration-500",
                cat === "doctor" && "bg-accent-cyan",
                cat === "lawyer" && "bg-accent-purple",
                cat === "salon" && "bg-accent-pink"
              )}
            />
          </motion.button>
        );
      })}
    </motion.div>
  );
}
