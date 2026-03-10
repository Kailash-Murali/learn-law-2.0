"use client"

import { useState, useEffect, useRef } from "react"
import { Check, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface XaiMicroFeedbackProps {
  featureName: string
  /** Only show after this many ms of panel visibility */
  delayMs?: number
  /** Whether the panel is currently visible */
  visible: boolean
  className?: string
}

/**
 * Minimal "Did this help verify the claim?" Yes/No widget.
 * Appears only after the user has viewed the XAI panel for at least `delayMs`.
 */
export function XaiMicroFeedback({
  featureName,
  delayMs = 3000,
  visible,
  className,
}: XaiMicroFeedbackProps) {
  const [show, setShow] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (visible && !submitted) {
      timerRef.current = setTimeout(() => setShow(true), delayMs)
    } else {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (!visible) setShow(false)
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [visible, delayMs, submitted])

  function send(rating: number) {
    setSubmitted(true)
    const payload = {
      message_id: `xai-feedback-${featureName}-${Date.now()}`,
      vote: rating >= 4 ? "up" : "down",
      xai_feature_used: featureName,
      user_rating: rating,
    }
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], { type: "application/json" })
      navigator.sendBeacon("/api/feedback", blob)
    } else {
      const schedule = typeof requestIdleCallback !== "undefined" ? requestIdleCallback : (cb: () => void) => setTimeout(cb, 0)
      schedule(() => {
        fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          keepalive: true,
        }).catch(() => {})
      })
    }
  }

  if (!show && !submitted) return null

  if (submitted) {
    return (
      <p className={cn("text-[10px] text-background/40 select-none", className)}>
        Thanks for the feedback!
      </p>
    )
  }

  return (
    <div className={cn("flex items-center gap-2 text-[10px] text-background/50", className)}>
      <span>Did this help verify the claim?</span>
      <button
        onClick={() => send(5)}
        aria-label="Yes, helpful"
        className="p-0.5 rounded hover:bg-green-500/20 hover:text-green-400 transition-colors cursor-pointer"
      >
        <Check className="size-3" />
      </button>
      <button
        onClick={() => send(1)}
        aria-label="No, not helpful"
        className="p-0.5 rounded hover:bg-red-500/20 hover:text-red-400 transition-colors cursor-pointer"
      >
        <X className="size-3" />
      </button>
    </div>
  )
}
