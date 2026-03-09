"use client"

import { useState } from "react"
import { Scale, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface ContrastiveData {
  contrastive_points?: string[]
  counterfactuals?: string[]
  key_distinctions?: string[]
}

interface ContrastivePanelProps {
  data: ContrastiveData | null | undefined
  className?: string
}

const SECTIONS: { key: keyof ContrastiveData; label: string; color: string }[] = [
  { key: "contrastive_points",  label: "Distinguishing factors",    color: "text-sky-400" },
  { key: "counterfactuals",     label: "Counterfactual scenarios",  color: "text-amber-400" },
  { key: "key_distinctions",    label: "Key legal distinctions",    color: "text-emerald-400" },
]

export function ContrastivePanel({ data, className }: ContrastivePanelProps) {
  const [open, setOpen] = useState(false)

  if (!data) return null

  const hasContent = SECTIONS.some(
    ({ key }) => Array.isArray(data[key]) && (data[key] as string[]).length > 0
  )
  if (!hasContent) return null

  const totalPoints = SECTIONS.reduce(
    (sum, { key }) => sum + ((data[key] as string[] | undefined)?.length ?? 0),
    0
  )

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden mt-2", className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-background/5 transition-colors"
        aria-expanded={open}
        aria-label="Contrastive and counterfactual analysis"
      >
        <Scale className="size-4 shrink-0 text-background/40" aria-hidden />
        <span className="flex-1 text-xs font-medium text-background/50">Contrastive Analysis</span>
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
          {SECTIONS.map(({ key, label, color }) => {
            const items = data[key] as string[] | undefined
            if (!items || items.length === 0) return null
            return (
              <div key={key}>
                <p className={cn("text-[10px] font-semibold uppercase tracking-wider mb-1", color)}>
                  {label}
                </p>
                <ul className="space-y-1.5">
                  {items.map((item, i) => (
                    <li
                      key={i}
                      className="flex gap-2 text-xs text-background/60 leading-relaxed"
                    >
                      <span className="mt-0.5 shrink-0 text-background/25">▸</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
