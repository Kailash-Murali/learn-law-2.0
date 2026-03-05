"use client"

import { cn } from "@/lib/utils"

interface ConfidenceIndicatorProps {
  level: "high" | "medium" | "low"
  className?: string
  showLabel?: boolean
}

const CONF = {
  high:   { dots: [true, true, true],  label: "High",   color: "bg-green-400" },
  medium: { dots: [true, true, false],  label: "Medium", color: "bg-yellow-400" },
  low:    { dots: [true, false, false], label: "Low",    color: "bg-red-400" },
} as const

export function ConfidenceIndicator({ level, className, showLabel = true }: ConfidenceIndicatorProps) {
  const conf = CONF[level] ?? CONF.medium
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} aria-label={`Confidence: ${conf.label}`}>
      <span className="inline-flex gap-0.5">
        {conf.dots.map((on, i) => (
          <span
            key={i}
            className={cn(
              "size-1.5 rounded-full",
              on ? conf.color : "bg-background/20"
            )}
          />
        ))}
      </span>
      {showLabel && (
        <span className="text-[10px] uppercase tracking-wider font-medium text-background/60">
          {conf.label}
        </span>
      )}
    </span>
  )
}
