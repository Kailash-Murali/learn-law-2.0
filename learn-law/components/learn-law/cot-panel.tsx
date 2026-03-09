"use client"

import { useState } from "react"
import { Brain, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface ReasoningStep {
  agent: string
  step: string
  details: Record<string, any>
  timestamp: string
}

interface CotPanelProps {
  traces: Record<string, ReasoningStep[]>
  className?: string
}

const AGENT_COLORS: Record<string, string> = {
  UIAgent:            "text-blue-400",
  ResearchAgent:      "text-green-400",
  XAIValidationAgent: "text-yellow-400",
  DocumentationAgent: "text-purple-400",
  DraftingAgent:      "text-orange-400",
}

export function CotPanel({ traces, className }: CotPanelProps) {
  const [open, setOpen] = useState(false)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  const agents = Object.entries(traces).filter(([, steps]) => Array.isArray(steps) && steps.length > 0)
  const totalSteps = agents.reduce((sum, [, steps]) => sum + steps.length, 0)

  if (totalSteps === 0) return null

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden mt-2", className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-background/5 transition-colors"
        aria-expanded={open}
        aria-label="Chain of Thought – reasoning traces"
      >
        <Brain className="size-4 shrink-0 text-background/40" aria-hidden />
        <span className="flex-1 text-xs font-medium text-background/50">Chain of Thought</span>
        <span className="text-[10px] text-background/30 mr-2">
          {agents.length} agents · {totalSteps} steps
        </span>
        <ChevronRight
          className={cn(
            "size-3.5 text-background/30 transition-transform duration-200",
            open && "rotate-90"
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div className="border-t border-background/10 px-3 py-2 space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
          {agents.map(([agentName, steps]) => {
            const isExpanded = expandedAgent === agentName
            const colorClass = AGENT_COLORS[agentName] ?? "text-background/60"

            return (
              <div key={agentName} className="rounded border border-background/10">
                <button
                  onClick={() => setExpandedAgent(isExpanded ? null : agentName)}
                  className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left hover:bg-background/5 transition-colors"
                  aria-expanded={isExpanded}
                >
                  <span
                    className={cn(
                      "text-[10px] font-semibold font-mono uppercase tracking-wider",
                      colorClass
                    )}
                  >
                    {agentName}
                  </span>
                  <span className="flex-1 text-[10px] text-background/30">{steps.length} steps</span>
                  <ChevronRight
                    className={cn(
                      "size-3 text-background/25 transition-transform duration-150",
                      isExpanded && "rotate-90"
                    )}
                    aria-hidden
                  />
                </button>

                {isExpanded && (
                  <div className="px-2.5 pb-2 pt-0.5 border-t border-background/10 space-y-2 animate-in fade-in slide-in-from-top-1 duration-150">
                    {steps.map((step, i) => (
                      <div key={i} className="flex gap-2 text-[10px]">
                        <span className="text-background/20 shrink-0 pt-0.5 font-mono tabular-nums">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <div className="min-w-0">
                          <span className="text-background/50 font-medium">{step.step}</span>
                          {step.details?.rationale ? (
                            <p className="text-background/35 mt-0.5 leading-relaxed">
                              {step.details.rationale}
                            </p>
                          ) : step.details?.action ? (
                            <p className="text-background/35 mt-0.5">{step.details.action}</p>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
