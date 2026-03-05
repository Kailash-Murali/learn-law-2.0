"use client"

import { cn } from "@/lib/utils"

interface RiskScoreBadgeProps {
  score: number        // 0.0 – 1.0
  label: string        // LOW | MEDIUM | HIGH
  className?: string
  size?: "sm" | "md"
}

const RISK_COLORS = {
  LOW:    { ring: "text-green-400",  bg: "bg-green-400/15", text: "text-green-300" },
  MEDIUM: { ring: "text-yellow-400", bg: "bg-yellow-400/15", text: "text-yellow-300" },
  HIGH:   { ring: "text-red-400",    bg: "bg-red-400/15",    text: "text-red-300" },
} as const

export function RiskScoreBadge({ score, label, className, size = "md" }: RiskScoreBadgeProps) {
  const pct = Math.round(score * 100)
  const colors = RISK_COLORS[label as keyof typeof RISK_COLORS] ?? RISK_COLORS.MEDIUM

  // SVG circular progress
  const radius = size === "sm" ? 16 : 22
  const stroke = size === "sm" ? 3 : 3.5
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score * circumference)
  const viewBox = (radius + stroke) * 2
  const center = radius + stroke

  const sizeCls = size === "sm" ? "size-10" : "size-14"

  return (
    <div className={cn("inline-flex flex-col items-center gap-1", className)} aria-label={`Risk score: ${pct}% — ${label}`}>
      <div className={cn("relative", sizeCls)}>
        <svg viewBox={`0 0 ${viewBox} ${viewBox}`} className="w-full h-full -rotate-90">
          {/* Background ring */}
          <circle cx={center} cy={center} r={radius} fill="none" stroke="currentColor" strokeWidth={stroke} className="text-background/10" />
          {/* Progress ring */}
          <circle
            cx={center} cy={center} r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={cn("transition-all duration-500", colors.ring)}
          />
        </svg>
        {/* Center label */}
        <span className={cn(
          "absolute inset-0 flex items-center justify-center font-semibold",
          size === "sm" ? "text-[10px]" : "text-xs",
          colors.text
        )}>
          {pct}%
        </span>
      </div>
      <span className={cn(
        "uppercase tracking-wider font-semibold",
        size === "sm" ? "text-[9px]" : "text-[10px]",
        colors.text
      )}>
        {label}
      </span>
    </div>
  )
}
