"use client"

import { useState } from "react"
import { ChevronRight, ExternalLink, BookOpen, ScrollText, CheckCircle2, AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"
import { ValidationStatusBanner } from "./validation-status-banner"
import { RiskScoreBadge } from "./risk-score-badge"

interface Citation {
  name: string
  url?: string | null
  verified: boolean
}

interface CitationVerificationListProps {
  citations: Citation[]
  statutes: Citation[]
  articleRefs?: string[]
  isGrounded?: boolean
  riskLabel?: string
  riskScore?: number
  ikAvailable?: boolean
  className?: string
}

export function CitationVerificationList({
  citations,
  statutes,
  articleRefs = [],
  isGrounded,
  riskLabel,
  riskScore,
  ikAvailable,
  className,
}: CitationVerificationListProps) {
  const [open, setOpen] = useState(false)

  const totalCitations = citations.length
  const verifiedCitations = citations.filter((c) => c.verified).length
  const totalStatutes = statutes.length
  const verifiedStatutes = statutes.filter((s) => s.verified).length
  const totalItems = totalCitations + totalStatutes
  const totalVerified = verifiedCitations + verifiedStatutes

  const hasValidation = riskLabel !== undefined && riskScore !== undefined

  if (totalItems === 0 && articleRefs.length === 0 && !hasValidation) return null

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden", className)}>
      {/* ── Collapsed header ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-2.5 hover:bg-background/5 transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <BookOpen className="size-4 shrink-0 text-background/50" aria-hidden />
        <span className="text-sm font-medium text-background/80 flex-1 text-left">
          Sources &amp; Validation
          {totalItems > 0 && (
            <span className="text-background/40 font-normal ml-1.5">
              ({totalVerified}/{totalItems} verified)
            </span>
          )}
        </span>

        {/* Mini stats */}
        <div className="flex items-center gap-2 text-[11px] text-background/40 shrink-0">
          {totalCitations > 0 && (
            <span className="flex items-center gap-1">
              <CheckCircle2 className="size-3 text-green-400" aria-hidden />
              {verifiedCitations}
            </span>
          )}
          {totalCitations - verifiedCitations > 0 && (
            <span className="flex items-center gap-1">
              <AlertTriangle className="size-3 text-yellow-400" aria-hidden />
              {totalCitations - verifiedCitations}
            </span>
          )}
        </div>

        <ChevronRight
          className={cn("size-4 text-background/30 transition-transform duration-200", open && "rotate-90")}
          aria-hidden
        />
      </button>

      {/* ── Expanded list ── */}
      {open && (
        <div className="border-t border-background/10 animate-in fade-in slide-in-from-top-1 duration-200">
          {/* Case citations */}
          {totalCitations > 0 && (
            <div className="px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium mb-2 flex items-center gap-1.5">
                <BookOpen className="size-3" aria-hidden />
                Case Citations ({verifiedCitations}/{totalCitations} verified)
              </p>
              <ul className="space-y-1.5" role="list">
                {citations.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    {c.verified ? (
                      <CheckCircle2 className="size-3.5 shrink-0 mt-0.5 text-green-400" aria-label="Verified" />
                    ) : (
                      <AlertTriangle className="size-3.5 shrink-0 mt-0.5 text-yellow-400" aria-label="Unverified" />
                    )}
                    <div className="min-w-0 flex-1">
                      <span className="text-background/70">{c.name}</span>
                      {c.url && (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 hover:underline mt-0.5"
                        >
                          <ExternalLink className="size-2.5" aria-hidden />
                          Indian Kanoon
                        </a>
                      )}
                      {!c.verified && !c.url && (
                        <span className="text-[11px] text-background/30 block mt-0.5">Not found on Indian Kanoon</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Statutes */}
          {totalStatutes > 0 && (
            <div className={cn("px-3 py-2.5", totalCitations > 0 && "border-t border-background/10")}>
              <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium mb-2 flex items-center gap-1.5">
                <ScrollText className="size-3" aria-hidden />
                Statutes ({verifiedStatutes}/{totalStatutes} verified)
              </p>
              <ul className="space-y-1.5" role="list">
                {statutes.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    {s.verified ? (
                      <CheckCircle2 className="size-3.5 shrink-0 mt-0.5 text-green-400" aria-label="Verified" />
                    ) : (
                      <AlertTriangle className="size-3.5 shrink-0 mt-0.5 text-yellow-400" aria-label="Unverified" />
                    )}
                    <div className="min-w-0 flex-1">
                      <span className="text-background/70">{s.name}</span>
                      {s.url && (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 hover:underline mt-0.5"
                        >
                          <ExternalLink className="size-2.5" aria-hidden />
                          Indian Kanoon
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Article refs */}
          {articleRefs.length > 0 && (
            <div className={cn("px-3 py-2.5", (totalCitations > 0 || totalStatutes > 0) && "border-t border-background/10")}>
              <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium mb-2">
                Constitutional Articles Referenced
              </p>
              <div className="flex flex-wrap gap-1.5">
                {articleRefs.map((ref, i) => (
                  <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 font-medium">
                    {ref}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── Validation section ── */}
          {hasValidation && (
            <div className={cn("px-3 py-2.5 flex items-center gap-3", (totalItems > 0 || articleRefs.length > 0) && "border-t border-background/10")}>
              <ValidationStatusBanner
                isGrounded={isGrounded!}
                riskLabel={riskLabel!}
                ikAvailable={ikAvailable!}
                className="flex-1 rounded-none bg-transparent px-0 py-0"
              />
              <RiskScoreBadge score={riskScore!} label={riskLabel!} size="sm" className="shrink-0" />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
