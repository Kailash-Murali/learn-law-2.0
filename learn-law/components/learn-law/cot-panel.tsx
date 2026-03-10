"use client"

import { useState, useCallback, useRef } from "react"
import { Brain, ChevronRight, GitBranch } from "lucide-react"
import { cn } from "@/lib/utils"
import { useXaiTelemetry } from "@/hooks/use-xai-telemetry"
import { XaiMicroFeedback } from "./xai-micro-feedback"

interface ReasoningStep {
  agent: string
  step: string
  details: Record<string, any>
  timestamp: string
}

interface CotPanelProps {
  traces: Record<string, ReasoningStep[]>
  validation?: Record<string, unknown>
  className?: string
}

const AGENT_COLORS: Record<string, string> = {
  UIAgent:            "text-blue-400",
  ResearchAgent:      "text-green-400",
  XAIValidationAgent: "text-yellow-400",
  DocumentationAgent: "text-purple-400",
  DraftingAgent:      "text-orange-400",
}

/* ── Surrogate tree types ── */
interface TreeNode {
  id: number
  label: string
  type: "decision" | "leaf"
  prediction?: boolean | null
  children?: TreeNode[]
}

interface TreeData {
  accuracy: number
  nodes: TreeNode[]
  feature_names: string[]
}

/* ── Recursive tree renderer ── */
function TreeNodeView({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const isLeaf = node.type === "leaf"
  const prediction = node.prediction

  return (
    <div className="flex flex-col items-center">
      {/* Node box */}
      <div
        className={cn(
          "relative rounded-md border px-3 py-1.5 text-[10px] text-center max-w-[200px] leading-tight",
          isLeaf
            ? prediction
              ? "border-green-500/40 bg-green-500/10 text-green-300"
              : "border-red-500/40 bg-red-500/10 text-red-300"
            : "border-background/20 bg-background/5 text-background/60"
        )}
      >
        {node.label}
      </div>

      {/* Children container */}
      {node.children && node.children.length > 0 && (
        <div className="flex flex-col items-center mt-1">
          {/* Vertical connector from parent */}
          <div className="w-px h-3 bg-background/15" />
          {/* Horizontal bar spanning children */}
          {node.children.length > 1 && (
            <div
              className="h-px bg-background/15"
              style={{ width: `${Math.max(60, node.children.length * 100)}px` }}
            />
          )}
          {/* Children row */}
          <div className="flex gap-4 mt-0">
            {node.children.map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="w-px h-3 bg-background/15" />
                <TreeNodeView node={child} depth={depth + 1} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function CotPanel({ traces, validation, className }: CotPanelProps) {
  const [open, setOpen] = useState(false)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [treeOpen, setTreeOpen] = useState(false)
  const [treeData, setTreeData] = useState<TreeData | null>(null)
  const [treeLoading, setTreeLoading] = useState(false)
  const treeFetched = useRef(false)
  const { onOpen: treeOnOpen, onClose: treeOnClose } = useXaiTelemetry("surrogate_tree")

  const agents = Object.entries(traces).filter(([, steps]) => Array.isArray(steps) && steps.length > 0)
  const totalSteps = agents.reduce((sum, [, steps]) => sum + steps.length, 0)

  if (totalSteps === 0) return null

  const handleTreeToggle = useCallback(() => {
    const next = !treeOpen
    setTreeOpen(next)
    if (next) {
      treeOnOpen()
      if (!treeFetched.current && validation) {
        treeFetched.current = true
        setTreeLoading(true)
        fetch("/api/xai/surrogate-tree", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ validation_data: validation }),
        })
          .then((r) => (r.ok ? r.json() : null))
          .then((data) => { if (data) setTreeData(data) })
          .catch(() => {})
          .finally(() => setTreeLoading(false))
      }
    } else {
      treeOnClose()
    }
  }, [treeOpen, validation, treeOnOpen, treeOnClose])

  /* Build a tree from flat nodes array */
  function buildTree(nodes: { id: number; label: string; type: string; prediction?: boolean | null; children_ids?: number[] }[]): TreeNode[] {
    const map = new Map<number, TreeNode>()
    for (const n of nodes) {
      map.set(n.id, { id: n.id, label: n.label, type: n.type as "decision" | "leaf", prediction: n.prediction ?? null, children: [] })
    }
    const roots: TreeNode[] = []
    const childSet = new Set<number>()
    for (const n of nodes) {
      if (n.children_ids) {
        for (const cid of n.children_ids) {
          childSet.add(cid)
          const parent = map.get(n.id)
          const child = map.get(cid)
          if (parent && child) parent.children!.push(child)
        }
      }
    }
    for (const n of nodes) {
      if (!childSet.has(n.id)) roots.push(map.get(n.id)!)
    }
    return roots
  }

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

          {/* ── Surrogate decision tree section ── */}
          {validation && (
            <div className="rounded border border-background/10">
              <button
                onClick={handleTreeToggle}
                className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left hover:bg-background/5 transition-colors"
                aria-expanded={treeOpen}
              >
                <GitBranch className="size-3 shrink-0 text-yellow-400" aria-hidden />
                <span className="text-[10px] font-semibold font-mono uppercase tracking-wider text-yellow-400">
                  AI Logic Path
                </span>
                <span className="flex-1 text-[10px] text-background/30">Surrogate Decision Tree</span>
                <ChevronRight
                  className={cn("size-3 text-background/25 transition-transform duration-150", treeOpen && "rotate-90")}
                  aria-hidden
                />
              </button>

              {treeOpen && (
                <div className="px-2.5 pb-3 pt-1.5 border-t border-background/10 animate-in fade-in slide-in-from-top-1 duration-150">
                  {treeLoading && (
                    <div className="space-y-2 animate-pulse">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="h-6 rounded bg-background/5" />
                      ))}
                    </div>
                  )}

                  {treeData && (
                    <div className="space-y-3">
                      {/* Accuracy badge */}
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-background/40">Surrogate fidelity:</span>
                        <span
                          className={cn(
                            "text-[10px] font-mono px-1.5 py-0.5 rounded",
                            treeData.accuracy >= 0.85
                              ? "bg-green-500/20 text-green-300"
                              : treeData.accuracy >= 0.65
                              ? "bg-yellow-500/20 text-yellow-300"
                              : "bg-red-500/20 text-red-300"
                          )}
                        >
                          {(treeData.accuracy * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Tree flowchart */}
                      <div className="overflow-x-auto py-2">
                        <div className="flex flex-col items-center min-w-fit">
                          {buildTree(treeData.nodes as any).map((root) => (
                            <TreeNodeView key={root.id} node={root} />
                          ))}
                        </div>
                      </div>

                      <XaiMicroFeedback featureName="surrogate_tree" visible={treeOpen} />
                    </div>
                  )}

                  {!treeLoading && !treeData && (
                    <p className="text-[10px] text-background/30">Could not load decision tree.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
