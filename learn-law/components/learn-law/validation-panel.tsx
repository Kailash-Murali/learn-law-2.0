"use client"

import { useState } from "react"
import { AlertOctagon, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { ValidationStatusBanner } from "./validation-status-banner"
import { RiskScoreBadge } from "./risk-score-badge"
import { BadLawCard, type BadLaw } from "./bad-law-card"
import { CitationVerificationList } from "./citation-verification-list"

interface Citation {
  name: string
  url?: string | null
  verified: boolean
}

export interface ValidationData {
  is_grounded: boolean
  risk_label: string
  risk_score: number
  ik_available: boolean
  citations: Citation[]
  statutes: Citation[]
  bad_laws: BadLaw[]
  article_refs: string[]
}

interface ValidationPanelProps {
  validation: ValidationData
  className?: string
}

export function ValidationPanel({ validation, className }: ValidationPanelProps) {
  const {
    is_grounded,
    risk_label,
    risk_score,
    ik_available,
    citations,
    statutes,
    bad_laws,
    article_refs,
  } = validation

  const [badLawsOpen, setBadLawsOpen] = useState(false)

  const hasBadLaws = bad_laws && bad_laws.length > 0
  const criticalCount = hasBadLaws ? bad_laws.length : 0
  const hasSources =
    (citations && citations.length > 0) ||
    (statutes && statutes.length > 0) ||
    (article_refs && article_refs.length > 0)

  return (
    <div className={cn("space-y-2.5 mt-3", className)}>
      {/* ── Row 1: Bad laws accordion ── */}
      {hasBadLaws && (
        <div className="rounded-lg border border-background/10 overflow-hidden">
          <button
            onClick={() => setBadLawsOpen((v) => !v)}
            className="flex w-full items-center gap-3 px-3 py-2.5 hover:bg-background/5 transition-colors cursor-pointer"
            aria-expanded={badLawsOpen}
          >
            <AlertOctagon className="size-4 shrink-0 text-red-400" aria-hidden />
            <span className="text-sm font-medium text-background/80 flex-1 text-left">
              Repealed / Unconstitutional Laws
            </span>
            {criticalCount > 0 && (
              <span className="shrink-0 text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-300">
                {criticalCount}
              </span>
            )}
            <ChevronRight
              className={cn("size-4 text-background/30 transition-transform duration-200", badLawsOpen && "rotate-90")}
              aria-hidden
            />
          </button>

          {badLawsOpen && (
            <div className="border-t border-background/10 px-3 py-2.5 space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
              {bad_laws.map((bl, i) => (
                <BadLawCard key={`${bl.law}-${i}`} badLaw={bl} defaultOpen={i === 0} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Row 2: Sources & Validation ── */}
      <CitationVerificationList
        citations={citations ?? []}
        statutes={statutes ?? []}
        articleRefs={article_refs ?? []}
        isGrounded={is_grounded}
        riskLabel={risk_label}
        riskScore={risk_score}
        ikAvailable={ik_available}
      />
    </div>
  )
}
