"use client"

import { useState, useEffect, useRef } from "react"
import { Scale, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useXaiTelemetry } from "@/hooks/use-xai-telemetry"
import { XaiMicroFeedback } from "./xai-micro-feedback"

interface ContrastiveData {
  contrastive_points?: string[]
  counterfactuals?: string[]
  key_distinctions?: string[]
}

interface DiceCF {
  features: Record<string, unknown>
  outcome: string
  changed_fields: string[]
}
interface DiceResult {
  original: Record<string, unknown> & { outcome: string }
  counterfactuals: DiceCF[]
}

const FEATURE_DISPLAY: Record<string, string> = {
  is_mandatory_sentence: "Mandatory sentence",
  allows_judicial_discretion: "Judicial discretion",
  cites_fundamental_rights: "Fundamental Rights cited",
  is_central_legislation: "Central legislation",
  has_criminal_provision: "Criminal provision",
  applicable_act: "Applicable Act",
}

interface ContrastivePanelProps {
  data: ContrastiveData | null | undefined
  queryType?: string
  diceFeatures?: Record<string, unknown> | null
  userQuery?: string
  className?: string
}

const SECTIONS: { key: keyof ContrastiveData; label: string }[] = [
  { key: "contrastive_points", label: "Distinguishing factors" },
  { key: "key_distinctions", label: "Key legal distinctions" },
]

// ── DiCE comparative table ───────────────────────────────────────────
function DiceTable({ result }: { result: DiceResult }) {
  const featureKeys = Object.keys(result.original).filter((k) => k !== "outcome")
  const cfs = result.counterfactuals

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b border-background/10">
            <th className="text-left py-1.5 pr-3 text-background/50 font-medium">Feature</th>
            <th className="text-left py-1.5 px-2 text-background/50 font-medium">Original</th>
            {cfs.map((_, i) => (
              <th key={i} className="text-left py-1.5 px-2 text-background/50 font-medium">
                CF{i + 1}
                <span className="ml-1 text-[9px] text-yellow-400/70 font-normal">
                  ({cfs[i].changed_fields.length} changes)
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {featureKeys.map((key) => (
            <tr key={key} className="border-b border-background/5">
              <td className="py-1.5 pr-3 text-background/60 font-medium">
                {FEATURE_DISPLAY[key] ?? key}
              </td>
              <td className="py-1.5 px-2 text-background/70">{String(result.original[key])}</td>
              {cfs.map((cf, i) => {
                const changed = cf.changed_fields.includes(key)
                return (
                  <td
                    key={i}
                    className={cn(
                      "py-1.5 px-2",
                      changed
                        ? "bg-yellow-400/20 text-yellow-200 font-semibold rounded"
                        : "text-background/70"
                    )}
                  >
                    {String(cf.features[key] ?? result.original[key])}
                  </td>
                )
              })}
            </tr>
          ))}
          {/* Outcome row */}
          <tr className="border-t border-background/15">
            <td className="py-2 pr-3 text-background/80 font-semibold">Predicted Outcome</td>
            <td className="py-2 px-2 text-green-400 font-semibold">{result.original.outcome}</td>
            {cfs.map((cf, i) => (
              <td key={i} className="py-2 px-2 text-red-400 font-semibold">
                {cf.outcome}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export function ContrastivePanel({ data, queryType = "advisory", diceFeatures, userQuery, className }: ContrastivePanelProps) {
  const [open, setOpen] = useState(false)
  const { onOpen, onClose } = useXaiTelemetry("dice_table")
  const isClassification = queryType === "classification"

  // DiCE state
  const [diceResult, setDiceResult] = useState<DiceResult | null>(null)
  const [diceLoading, setDiceLoading] = useState(false)
  const diceFetched = useRef(false)

  if (!data) return null

  const hasLegacyCounterfactuals = Array.isArray(data.counterfactuals) && data.counterfactuals.length > 0
  const hasContent =
    SECTIONS.some(({ key }) => Array.isArray(data[key]) && (data[key] as string[]).length > 0) ||
    hasLegacyCounterfactuals

  if (!hasContent) return null

  const totalPoints = SECTIONS.reduce(
    (sum, { key }) => sum + ((data[key] as string[] | undefined)?.length ?? 0),
    0
  ) + (hasLegacyCounterfactuals ? data.counterfactuals!.length : 0)

  function handleToggle() {
    const next = !open
    setOpen(next)
    if (next) {
      onOpen()
      // Fetch DiCE counterfactuals on first open (classification queries only)
      if (!diceFetched.current && isClassification) {
        diceFetched.current = true
        setDiceLoading(true)
        fetch("/api/xai/counterfactuals", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_query: userQuery ?? "",
            case_features: diceFeatures ?? null,
          }),
        })
          .then((r) => (r.ok ? r.json() : null))
          .then((d) => { if (d && d.counterfactuals) setDiceResult(d) })
          .catch(() => {})
          .finally(() => setDiceLoading(false))
      }
    } else {
      onClose()
    }
  }

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden mt-2", className)}>
      <button
        onClick={handleToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-background/5 transition-colors"
        aria-expanded={open}
        aria-label="Contrastive and counterfactual analysis"
      >
        <Scale className="size-5 shrink-0 text-background/40" aria-hidden />
        <span className="flex-1 text-sm font-medium text-background/80">Contrastive Analysis</span>
        <span className="text-[10px] text-background/30 mr-2">{totalPoints} points</span>
        <ChevronRight
          className={cn(
            "size-3.5 text-background/30 transition-transform duration-200",
            open && "rotate-90"
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div className="border-t border-background/10 px-3 py-2 space-y-3 animate-in fade-in slide-in-from-top-1 duration-200">
          {/* Non-counterfactual sections (contrastive_points, key_distinctions) */}
          {SECTIONS.map(({ key, label }) => {
            const items = data[key] as string[] | undefined
            if (!items || items.length === 0) return null
            return (
              <div key={key}>
                <p className={cn("text-[12px] font-semibold uppercase tracking-wider mb-1")}>
                  {label}
                </p>
                <ul className="space-y-1.5">
                  {items.map((item, i) => (
                    <li key={i} className="flex gap-2 text-xs text-background/60 leading-relaxed">
                      <span className="mt-0.5 shrink-0 text-background/25">▸</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}

          {/* DiCE counterfactual table */}
          {isClassification ? (
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-wider mb-1">
                Counterfactual Scenarios (DiCE)
              </p>
              {diceLoading && (
                <div className="space-y-1.5 animate-pulse">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-4 rounded bg-background/10" />
                  ))}
                </div>
              )}
              {diceResult && <DiceTable result={diceResult} />}
              {!diceLoading && !diceResult && hasLegacyCounterfactuals && (
                <ul className="space-y-1.5">
                  {data.counterfactuals!.map((item, i) => (
                    <li key={i} className="flex gap-2 text-xs text-background/60 leading-relaxed">
                      <span className="mt-0.5 shrink-0 text-background/25">▸</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className="rounded border border-background/10 px-3 py-2">
              <p className="text-[11px] text-background/50 leading-relaxed">
                This is an advisory query — DiCE counterfactuals apply only to binary
                validity questions. Click any sentence in the answer above to explore
                source attribution via the Attention Map.
              </p>
            </div>
          )}

          <XaiMicroFeedback featureName="dice_table" visible={open} />
        </div>
      )}
    </div>
  )
}
