"use client"

import { useState } from "react"
import { ChevronRight, AlertOctagon, AlertTriangle, Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface FlagsSectionProps {
  flags: string[]
  className?: string
}

const SEVERITY_ORDER = ["critical", "warning", "info"] as const

function classifyFlag(flag: string): (typeof SEVERITY_ORDER)[number] {
  const lower = flag.toLowerCase()
  if (
    lower.includes("bad law") ||
    lower.includes("unconstitutional") ||
    lower.includes("struck down") ||
    lower.includes("repealed") ||
    lower.includes("critical")
  )
    return "critical"
  if (
    lower.includes("warning") ||
    lower.includes("caution") ||
    lower.includes("unverified") ||
    lower.includes("not found")
  )
    return "warning"
  return "info"
}

const SEVERITY_CONFIG = {
  critical: {
    icon: AlertOctagon,
    bg: "bg-red-500/8",
    border: "border-red-500/30",
    text: "text-red-300",
    dot: "bg-red-400",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-yellow-500/8",
    border: "border-yellow-500/30",
    text: "text-yellow-300",
    dot: "bg-yellow-400",
  },
  info: {
    icon: Info,
    bg: "bg-blue-500/8",
    border: "border-blue-500/30",
    text: "text-blue-300",
    dot: "bg-blue-400",
  },
} as const

export function FlagsSection({ flags, className }: FlagsSectionProps) {
  const [open, setOpen] = useState(false)

  if (!flags || flags.length === 0) return null

  const classified = flags.map((f) => ({ text: f, severity: classifyFlag(f) }))
  const criticalCount = classified.filter((f) => f.severity === "critical").length
  const warningCount = classified.filter((f) => f.severity === "warning").length

  // Sort: critical → warning → info
  classified.sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden", className)}>
      {/* ── Collapsed header ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-2.5 hover:bg-background/5 transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <AlertTriangle className="size-4 shrink-0 text-background/50" aria-hidden />
        <span className="text-sm font-medium text-background/80 flex-1 text-left">
          Flags
          <span className="text-background/40 font-normal ml-1.5">({flags.length})</span>
        </span>

        {/* Severity pills */}
        <div className="flex items-center gap-1.5 shrink-0">
          {criticalCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-300 font-medium">
              {criticalCount} critical
            </span>
          )}
          {warningCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-300 font-medium">
              {warningCount} warning
            </span>
          )}
        </div>

        <ChevronRight
          className={cn("size-4 text-background/30 transition-transform duration-200", open && "rotate-90")}
          aria-hidden
        />
      </button>

      {/* ── Expanded flags list ── */}
      {open && (
        <div className="border-t border-background/10 p-3 space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
          {classified.map((flag, i) => {
            const cfg = SEVERITY_CONFIG[flag.severity]
            const Icon = cfg.icon
            return (
              <div
                key={i}
                className={cn("flex items-start gap-2 text-xs px-2.5 py-2 rounded-md border", cfg.bg, cfg.border)}
              >
                <Icon className={cn("size-3.5 shrink-0 mt-0.5", cfg.text)} aria-hidden />
                <span className="text-background/70 leading-relaxed">{flag.text}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
