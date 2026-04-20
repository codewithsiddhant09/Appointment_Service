"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface VoiceButtonProps {
  onResult: (transcript: string) => void;
}

export default function VoiceButton({ onResult }: VoiceButtonProps) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const toggle = useCallback(() => {
    // Check browser support
    const SpeechRecognition =
      typeof window !== "undefined" &&
      ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
      setListening(false);
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [listening, onResult]);

  return (
    <motion.button
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
      onClick={toggle}
      className={cn(
        "relative w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 cursor-pointer",
        listening
          ? "bg-accent-pink/20 text-accent-pink glow-pink"
          : "glass text-white/50 hover:text-accent-cyan hover:glow-cyan"
      )}
      title={listening ? "Stop listening" : "Voice input"}
    >
      {listening ? <MicOff size={18} /> : <Mic size={18} />}

      {/* Pulsing ring when active */}
      <AnimatePresence>
        {listening && (
          <>
            <motion.span
              className="absolute inset-0 rounded-full border-2 border-accent-pink/40"
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 1.8, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 1.2, ease: "easeOut" }}
            />
            <motion.span
              className="absolute inset-0 rounded-full border-2 border-accent-pink/30"
              initial={{ scale: 1, opacity: 0.4 }}
              animate={{ scale: 2.2, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 1.2, ease: "easeOut", delay: 0.3 }}
            />
          </>
        )}
      </AnimatePresence>
    </motion.button>
  );
}
