"use client"

import { useState, useRef, useCallback } from "react"
import { Info, ChevronLeft, ChevronRight } from "lucide-react"

const CARDS = [
  {
    title: "Query Modes",
    body: (
      <ul className="space-y-2 text-xs text-background/70">
        <li><span className="font-medium text-background/90">Research</span> — finds relevant Springer peer-reviewed papers and generates a full report + PDF.</li>
        <li><span className="font-medium text-background/90">Draft</span> — produces a ready-to-use legal draft downloadable as Word.</li>
        <li><span className="font-medium text-background/90">Ask</span> — quick conversational answer with cited sources.</li>
      </ul>
    ),
  },
  {
    title: "Explainability",
    body: (
      <ul className="space-y-2 text-xs text-background/70">
        <li><span className="font-medium text-background/90">Grounding check</span> — verifies the answer is supported by cited sources.</li>
        <li><span className="font-medium text-background/90">Risk scoring</span> — numeric score &amp; label based on citation quality.</li>
        <li><span className="font-medium text-background/90">Repealed law detection</span> — flags struck-down or unconstitutional laws.</li>
      </ul>
    ),
  },
  {
    title: "How to Use",
    body: (
      <ul className="space-y-2 text-xs text-background/70">
        <li>Select a mode prefix — <span className="font-medium text-background/90">[research]</span> or <span className="font-medium text-background/90">[draft]</span> — or just type freely.</li>
        <li>Expand <span className="font-medium text-background/90">Sources &amp; Validation</span> below each answer to inspect citations and risk scores.</li>
        <li>Use the <span className="font-medium text-background/90">thumb buttons</span> on each reply to send feedback.</li>
      </ul>
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
            <div className="h-[130px] overflow-y-auto">
              {CARDS[page].body}
            </div>
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
                <button
                  key={i}
                  onClick={() => setPage(i)}
                  aria-label={`Go to page ${i + 1}`}
                  className={`size-1.5 rounded-full transition-colors cursor-pointer ${
                    i === page ? "bg-background/70" : "bg-background/20 hover:bg-background/40"
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