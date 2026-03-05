"use client"

import { cn } from "@/lib/utils"
import { ValidationStatusBanner } from "./validation-status-banner"
import { RiskScoreBadge } from "./risk-score-badge"
import { BadLawCard, type BadLaw } from "./bad-law-card"
import { CitationVerificationList } from "./citation-verification-list"
import { FlagsSection } from "./flags-section"
import { FeedbackSection } from "./feedback-section"

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
  feedback_id?: string
  citations: Citation[]
  statutes: Citation[]
  bad_laws: BadLaw[]
  article_refs: string[]
  flags: string[]
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
    feedback_id,
    citations,
    statutes,
    bad_laws,
    article_refs,
    flags,
  } = validation

  const hasBadLaws = bad_laws && bad_laws.length > 0
  const hasSources = (citations && citations.length > 0) || (statutes && statutes.length > 0) || (article_refs && article_refs.length > 0)
  const hasFlags = flags && flags.length > 0

  return (
    <div className={cn("space-y-2.5 mt-3", className)}>
      {/* ── Row 1: Status banner + Risk score ── */}
      <div className="flex items-start gap-3">
        <ValidationStatusBanner
          isGrounded={is_grounded}
          riskLabel={risk_label}
          ikAvailable={ik_available}
          className="flex-1"
        />
        <RiskScoreBadge score={risk_score} label={risk_label} size="sm" />
      </div>

      {/* ── Row 2: Bad laws (open by default, highest priority) ── */}
      {hasBadLaws && (
        <div className="space-y-1.5">
          <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium px-1">
            Repealed / Unconstitutional Laws ({bad_laws.length})
          </p>
          {bad_laws.map((bl, i) => (
            <BadLawCard key={`${bl.law}-${i}`} badLaw={bl} defaultOpen={i === 0} />
          ))}
        </div>
      )}

      {/* ── Row 3: Sources (collapsed by default) ── */}
      {hasSources && (
        <CitationVerificationList
          citations={citations}
          statutes={statutes}
          articleRefs={article_refs}
        />
      )}

      {/* ── Row 4: Flags (collapsed by default) ── */}
      {hasFlags && <FlagsSection flags={flags} />}

      {/* ── Row 5: Feedback ID ── */}
      {feedback_id && <FeedbackSection feedbackId={feedback_id} />}
    </div>
  )
}
