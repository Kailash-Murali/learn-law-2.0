"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { GitBranch, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useXaiTelemetry } from "@/hooks/use-xai-telemetry"
import { XaiMicroFeedback } from "./xai-micro-feedback"

interface CotPanelProps {
  validation?: Record<string, unknown>
  userQuery?: string
  className?: string
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

export function CotPanel({ validation, userQuery, className }: CotPanelProps) {
  const [open, setOpen] = useState(true)
  const [treeData, setTreeData] = useState<TreeData | null>(null)
  const [treeLoading, setTreeLoading] = useState(false)
  const treeFetched = useRef(false)
  const { onOpen, onClose } = useXaiTelemetry("surrogate_tree")

  if (!validation) return null

  const fetchTree = useCallback(() => {
    if (treeFetched.current) return
    treeFetched.current = true
    setTreeLoading(true)
    fetch("/api/xai/surrogate-tree", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_query: userQuery ?? "", validation_data: validation }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data) setTreeData(data) })
      .catch(() => {})
      .finally(() => setTreeLoading(false))
  }, [userQuery, validation])

  // Auto-fetch on mount (panel defaults to open)
  useEffect(() => { fetchTree() }, [fetchTree])

  const handleToggle = useCallback(() => {
    const next = !open
    setOpen(next)
    if (next) {
      onOpen()
      fetchTree()
    } else {
      onClose()
    }
  }, [open, onOpen, onClose, fetchTree])

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
        onClick={handleToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-background/5 transition-colors"
        aria-expanded={open}
        aria-label="AI Logic Path – Decision Tree"
      >
        <GitBranch className="size-4 shrink-0 text-yellow-400" aria-hidden />
        <span className="flex-1 text-small text-background/50">AI Logic Path · Decision Tree</span>
        <ChevronRight
          className={cn(
            "size-3.5 text-background/30 transition-transform duration-200",
            open && "rotate-90"
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div className="border-t border-background/10 px-3 py-2 animate-in fade-in slide-in-from-top-1 duration-200">
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

              <XaiMicroFeedback featureName="surrogate_tree" visible={open} />
            </div>
          )}

          {!treeLoading && !treeData && (
            <p className="text-[10px] text-background/30">Could not load decision tree.</p>
          )}
        </div>
      )}
    </div>
  )
}
