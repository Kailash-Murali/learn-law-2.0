"use client"

import { cn } from "@/lib/utils"
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react"

interface ValidationStatusBannerProps {
  isGrounded: boolean
  riskLabel: string
  ikAvailable: boolean
  className?: string
}

export function ValidationStatusBanner({ isGrounded, riskLabel, ikAvailable, className }: ValidationStatusBannerProps) {
  const isHigh = riskLabel === "HIGH"

  const state = isGrounded
    ? { icon: ShieldCheck, label: "Well-Grounded", desc: "Answer grounded in Indian law sources", color: "text-green-400", bg: "bg-green-400/10" }
    : isHigh
    ? { icon: ShieldX, label: "Ungrounded", desc: "No citations found — treat with caution", color: "text-red-400", bg: "bg-red-400/10" }
    : { icon: ShieldAlert, label: "Partially Grounded", desc: "Some claims lack direct citations", color: "text-yellow-400", bg: "bg-yellow-400/10" }

  const Icon = state.icon

  return (
    <div className={cn("flex items-center gap-3 rounded-lg px-3 py-2", state.bg, className)} role="status" aria-label={`Grounding: ${state.label}`}>
      <Icon className={cn("size-5 shrink-0", state.color)} aria-hidden />
      <div className="min-w-0">
        <p className={cn("text-xs font-semibold", state.color)}>{state.label}</p>
        <p className="text-[11px] text-background/50">{state.desc}</p>
      </div>
      {!ikAvailable && (
        <span className="ml-auto text-[10px] text-background/30 shrink-0">IK offline</span>
      )}
    </div>
  )
}
