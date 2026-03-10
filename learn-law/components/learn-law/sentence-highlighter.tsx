"use client"

import { useState, useCallback } from "react"
import { cn } from "@/lib/utils"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { useXaiTelemetry } from "@/hooks/use-xai-telemetry"
import { XaiMicroFeedback } from "./xai-micro-feedback"

interface SourceScore {
  name: string
  url: string
  score: number
}

interface SentenceMap {
  sentence: string
  sources: SourceScore[]
}

interface Citation {
  name: string
  url?: string | null
  verified?: boolean
}

interface SentenceHighlighterProps {
  text: string
  citations?: Citation[]
  className?: string
}

// Naive sentence splitter
function splitSentences(text: string): string[] {
  const parts = text.split(/(?<=[.!?])\s+(?=[A-Z])/)
  return parts.filter((s) => s.trim().length > 0)
}

export function SentenceHighlighter({ text, citations, className }: SentenceHighlighterProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeSentence, setActiveSentence] = useState<string | null>(null)
  const [sentenceMap, setSentenceMap] = useState<SentenceMap[] | null>(null)
  const [loading, setLoading] = useState(false)
  const { onOpen, onClose } = useXaiTelemetry("attention_map")

  const sentences = splitSentences(text)

  const handleClick = useCallback(
    (sentence: string) => {
      setActiveSentence(sentence)
      setDrawerOpen(true)
      onOpen()

      if (!citations || citations.length === 0) return

      setLoading(true)
      fetch("/api/xai/attention-map", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer_sentences: sentences,
          citations: citations
            .filter((c) => c.name)
            .map((c) => ({ name: c.name, url: c.url ?? "", text: c.name })),
        }),
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data?.sentence_source_map) setSentenceMap(data.sentence_source_map)
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    },
    [citations, sentences, onOpen],
  )

  const activeData = sentenceMap?.find((s) => s.sentence === activeSentence)

  return (
    <>
      <span className={className}>
        {sentences.map((sent, i) => (
          <span key={i}>
            <span
              onClick={() => handleClick(sent)}
              className="cursor-pointer hover:bg-yellow-400/10 hover:underline decoration-yellow-400/30 underline-offset-2 transition-colors rounded-sm px-0.5"
              title="Click to see source attribution"
            >
              {sent}
            </span>
            {i < sentences.length - 1 ? " " : ""}
          </span>
        ))}
      </span>

      <Sheet open={drawerOpen} onOpenChange={(v) => { setDrawerOpen(v); if (!v) onClose() }}>
        <SheetContent side="right" className="w-full sm:max-w-lg bg-foreground text-background overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-background text-sm">Source Attribution</SheetTitle>
            <SheetDescription className="text-background/50 text-xs">
              Similarity scores show how closely each source relates to the selected sentence.
            </SheetDescription>
          </SheetHeader>

          {/* Selected sentence */}
          <div className="px-4 pb-3">
            <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium mb-1">
              Selected Sentence
            </p>
            <blockquote className="text-xs text-background/80 italic border-l-2 border-yellow-400/50 pl-3 leading-relaxed">
              {activeSentence}
            </blockquote>
          </div>

          {/* Source scores */}
          <div className="px-4 space-y-3">
            <p className="text-[10px] uppercase tracking-wider text-background/40 font-medium">
              Source Documents
            </p>

            {loading && (
              <div className="space-y-2 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 rounded bg-background/10" />
                ))}
              </div>
            )}

            {activeData && activeData.sources.map((src, i) => (
              <div
                key={i}
                className="rounded-lg border border-background/10 p-3 space-y-1.5"
                style={{ backgroundColor: `rgba(255, 220, 50, ${src.score * 0.25})` }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-background/80 truncate flex-1">
                    {src.name}
                  </span>
                  <span
                    className={cn(
                      "text-[10px] font-mono px-1.5 py-0.5 rounded",
                      src.score >= 0.7
                        ? "bg-green-500/20 text-green-300"
                        : src.score >= 0.3
                        ? "bg-yellow-500/20 text-yellow-300"
                        : "bg-background/10 text-background/40"
                    )}
                  >
                    {(src.score * 100).toFixed(0)}%
                  </span>
                </div>
                {src.url && (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-blue-400 hover:underline truncate block"
                  >
                    {src.url}
                  </a>
                )}
                {/* Highlight bar */}
                <div className="h-1.5 rounded-full bg-background/10 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${src.score * 100}%`,
                      backgroundColor: `rgba(255, 220, 50, ${0.4 + src.score * 0.6})`,
                    }}
                  />
                </div>
              </div>
            ))}

            {!loading && !activeData && sentenceMap && (
              <p className="text-xs text-background/40">No source attribution data for this sentence.</p>
            )}
          </div>

          <div className="px-4 pt-3">
            <XaiMicroFeedback featureName="attention_map" visible={drawerOpen} />
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
