"use client"

import { useState } from "react"
import { ChevronRight, Ban, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import { ConfidenceIndicator } from "./confidence-indicator"

export interface BadLaw {
  law: string
  reason: string
  case?: string
  status?: string
  scope?: string
  year?: number
  confidence?: "high" | "medium" | "low"
  discussion_only?: boolean
}

interface BadLawCardProps {
  badLaw: BadLaw
  defaultOpen?: boolean
}

const STATUS_CONFIG: Record<string, { label: string; color: string; border: string }> = {
  struck_down_completely:    { label: "Struck Down",    color: "bg-red-500/20 text-red-300",    border: "border-l-red-500" },
  struck_down_partially:     { label: "Partial",        color: "bg-orange-500/20 text-orange-300", border: "border-l-orange-500" },
  stayed_enforcement:        { label: "Stayed",         color: "bg-yellow-500/20 text-yellow-300", border: "border-l-yellow-500" },
  under_review:              { label: "Under Review",   color: "bg-purple-500/20 text-purple-300", border: "border-l-purple-500" },
  under_constitutional_review: { label: "Under Review", color: "bg-purple-500/20 text-purple-300", border: "border-l-purple-500" },
  narrowly_interpreted:      { label: "Limited",        color: "bg-amber-500/20 text-amber-300",   border: "border-l-amber-500" },
}

function getStatusConfig(status?: string) {
  if (!status) return STATUS_CONFIG.struck_down_completely
  return STATUS_CONFIG[status] ?? STATUS_CONFIG.struck_down_completely
}

export function BadLawCard({ badLaw, defaultOpen = false }: BadLawCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const sc = getStatusConfig(badLaw.status)
  const confidence = badLaw.confidence ?? "medium"
  const isDicta = badLaw.discussion_only === true

  const currentYear = new Date().getFullYear()
  const yearsAgo = badLaw.year ? currentYear - badLaw.year : null

  return (
    <div
      className={cn(
        "rounded-lg border-l-[3px] transition-all duration-200",
        sc.border,
        isDicta
          ? "bg-background/5 border border-background/10"
          : "bg-background/8 border border-background/15 hover:border-background/25 hover:shadow-md hover:shadow-black/10"
      )}
    >
      {/* ── Header (always visible) ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left cursor-pointer"
        aria-expanded={open}
        aria-label={`${badLaw.law} — ${sc.label}`}
      >
        <Ban className="size-4 shrink-0 text-red-400" aria-hidden />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("text-sm font-medium truncate", isDicta && "italic text-background/60")}>
              {isDicta && "ⓘ "}
              {badLaw.law}
            </span>
          </div>
          <p className="text-xs text-background/50 mt-0.5 truncate">
            {sc.label}{badLaw.year ? ` (${badLaw.year})` : ""}
            {isDicta ? " — Discussion Only" : ""}
          </p>
        </div>

        {/* Right side: badges */}
        <div className="flex items-center gap-2 shrink-0">
          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded", sc.color)}>
            {sc.label}
          </span>
          <ConfidenceIndicator level={confidence} showLabel={false} />
          <ChevronRight
            className={cn("size-4 text-background/40 transition-transform duration-200", open && "rotate-90")}
            aria-hidden
          />
        </div>
      </button>

      {/* ── Expanded details ── */}
      {open && (
        <div className="px-4 pb-3 pt-1 border-t border-background/10 space-y-3 animate-in fade-in slide-in-from-top-1 duration-200">
          {/* Status / Scope / Confidence row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-background/40 block">Status</span>
              <span className="text-background/80 font-medium">{sc.label}</span>
            </div>
            {badLaw.scope && (
              <div>
                <span className="text-background/40 block">Scope</span>
                <span className="text-background/80">{badLaw.scope}</span>
              </div>
            )}
            <div>
              <span className="text-background/40 block">Confidence</span>
              <ConfidenceIndicator level={confidence} />
            </div>
          </div>

          {/* Year */}
          {badLaw.year && (
            <div className="text-xs text-background/50">
              Decided: {badLaw.year}
              {yearsAgo !== null && ` (${yearsAgo} year${yearsAgo !== 1 ? "s" : ""} ago)`}
            </div>
          )}

          {/* Holding */}
          {badLaw.reason && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-background/40 font-medium">Judicial Holding</span>
              <blockquote className="mt-1 pl-3 border-l-2 border-background/20 text-xs text-background/70 italic leading-relaxed">
                {badLaw.reason}
              </blockquote>
            </div>
          )}

          {/* Case citation */}
          {badLaw.case && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-background/40 font-medium">Found In</span>
              <p className="mt-1 text-xs text-background/70 flex items-center gap-1.5">
                <ExternalLink className="size-3 shrink-0 text-background/40" aria-hidden />
                {badLaw.case}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
