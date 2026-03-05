"use client"

import { useState, useRef, useCallback } from "react"
import { Info, ChevronLeft, ChevronRight } from "lucide-react"

const CARDS = [
  {
    title: "Query Modes",
    body: (
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-background/10">
            <th className="pb-1.5 pr-3 text-background/50 font-medium">Mode</th>
            <th className="pb-1.5 text-background/50 font-medium">What it does</th>
          </tr>
        </thead>
        <tbody className="text-background/70">
          <tr className="border-b border-background/5">
            <td className="py-1.5 pr-3 font-medium text-background/90">Research</td>
            <td className="py-1.5">Retrieves peer-reviewed Springer links relevant to your query</td>
          </tr>
          <tr className="border-b border-background/5">
            <td className="py-1.5 pr-3 font-medium text-background/90">Draft</td>
            <td className="py-1.5">Produces a ready-to-use legal draft you can download as Word</td>
          </tr>
          <tr>
            <td className="py-1.5 pr-3 font-medium text-background/90">Reports</td>
            <td className="py-1.5">Generates a structured legal report downloadable as PDF</td>
          </tr>
        </tbody>
      </table>
    ),
  },
  {
    title: "Explainability",
    body: (
      <ul className="space-y-2 text-xs text-background/70">
        <li><span className="font-medium text-background/90">Grounding check</span> — verifies if the answer is supported by cited sources.</li>
        <li><span className="font-medium text-background/90">Risk scoring</span> — numeric score &amp; label based on citation quality.</li>
        <li><span className="font-medium text-background/90">Citation verification</span> — each statute/case verified individually.</li>
        <li><span className="font-medium text-background/90">Repealed law detection</span> — flags struck-down or unconstitutional laws.</li>
      </ul>
    ),
  },
  {
    title: "How to Use",
    body: (
      <p className="text-xs text-background/70 leading-relaxed">
        Select a query mode — Research, Draft, or Reports — then type your question and press send.
        Expand the &ldquo;Sources &amp; Validation&rdquo; panel below each answer to inspect cited sources,
        grounding status, and risk scores before relying on the output.
      </p>
    ),
  },
] as const

export function AboutPopover() {
  const [open, setOpen] = useState(false)
  const [page, setPage] = useState(0)
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = useCallback(() => {
    if (leaveTimer.current) {
      clearTimeout(leaveTimer.current)
      leaveTimer.current = null
    }
  }, [])

  function handleEnter() {
    clearTimer()
    setOpen(true)
  }

  function handleLeave() {
    clearTimer()
    leaveTimer.current = setTimeout(() => setOpen(false), 200)
  }

  return (
    <div
      className="relative"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <button
        aria-label="About and features"
        className="p-0.5 rounded text-background/50 hover:text-background transition-colors"
      >
        <Info className="size-4" aria-hidden />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 z-50 w-72 rounded-xl border border-background/15 bg-foreground shadow-xl shadow-black/30 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="px-4 pt-3 pb-1">
            <h3 className="text-sm font-semibold text-background mb-2">
              {CARDS[page].title}
            </h3>
            {CARDS[page].body}
          </div>

          <div className="flex items-center justify-between px-4 py-2 border-t border-background/10">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              aria-label="Previous"
              className="p-1 rounded text-background/40 hover:text-background/70 disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <ChevronLeft className="size-4" aria-hidden />
            </button>

            <div className="flex items-center gap-1.5">
              {CARDS.map((_, i) => (
                <span
                  key={i}
                  className={`size-1.5 rounded-full transition-colors ${
                    i === page ? "bg-background/70" : "bg-background/20"
                  }`}
                />
              ))}
            </div>

            <button
              onClick={() => setPage((p) => Math.min(CARDS.length - 1, p + 1))}
              disabled={page === CARDS.length - 1}
              aria-label="Next"
              className="p-1 rounded text-background/40 hover:text-background/70 disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <ChevronRight className="size-4" aria-hidden />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}