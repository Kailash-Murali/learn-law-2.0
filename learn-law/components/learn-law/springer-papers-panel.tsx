"use client"

import { useState } from "react"
import { BookOpen, ChevronRight, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SpringerPaper {
  title: string
  authors: string | string[]
  abstract?: string
  doi?: string
  url?: string
  journal?: string
  publication_date?: string
  source?: string
  full_text_available?: boolean
}

interface SpringerPapersPanelProps {
  papers: SpringerPaper[]
  className?: string
}

export function SpringerPapersPanel({ papers, className }: SpringerPapersPanelProps) {
  const [open, setOpen] = useState(false)
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  if (!papers || papers.length === 0) return null

  return (
    <div className={cn("rounded-lg border border-background/10 overflow-hidden mt-2.5", className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-background/5 transition-colors"
        aria-expanded={open}
        aria-label={`Academic papers – ${papers.length} found`}
      >
        <BookOpen className="size-4 shrink-0 text-blue-400" aria-hidden />
        <span className="flex-1 text-sm font-medium text-background/80">Academic Papers</span>
        <span className="text-xs text-background/40 mr-2">{papers.length} found</span>
        <ChevronRight
          className={cn("size-4 text-background/40 transition-transform duration-200", open && "rotate-90")}
          aria-hidden
        />
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-2 border-t border-background/10 animate-in fade-in slide-in-from-top-1 duration-200">
          {papers.map((paper, idx) => {
            const isExpanded = expandedIdx === idx
            const authors = Array.isArray(paper.authors)
              ? paper.authors.join(", ")
              : paper.authors

            return (
              <div key={idx} className="rounded-md border border-background/10 bg-background/5">
                <button
                  onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                  className="flex w-full items-start gap-2 px-3 py-2 text-left"
                  aria-expanded={isExpanded}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-background/80 leading-snug">{paper.title}</p>
                    {authors && (
                      <p className="text-[10px] text-background/40 mt-0.5 truncate">{authors}</p>
                    )}
                  </div>
                  <ChevronRight
                    className={cn(
                      "size-3.5 shrink-0 text-background/30 mt-0.5 transition-transform duration-150",
                      isExpanded && "rotate-90"
                    )}
                    aria-hidden
                  />
                </button>

                {isExpanded && (
                  <div className="px-3 pb-2.5 pt-1.5 border-t border-background/10 space-y-2 animate-in fade-in slide-in-from-top-1 duration-150">
                    {paper.journal && (
                      <p className="text-[10px] text-background/50 italic">
                        {paper.journal}
                        {paper.publication_date ? ` · ${paper.publication_date}` : ""}
                      </p>
                    )}
                    {paper.abstract && typeof paper.abstract === "string" && (
                      <p className="text-xs text-background/60 leading-relaxed line-clamp-4">
                        {paper.abstract}
                      </p>
                    )}
                    <div className="flex items-center gap-3 flex-wrap">
                      {(paper.url || paper.doi) && (
                        <a
                          href={paper.url || `https://doi.org/${paper.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                          aria-label={`Open paper: ${paper.title}`}
                        >
                          <ExternalLink className="size-3" aria-hidden />
                          {paper.doi ? `doi:${paper.doi}` : "Open Paper"}
                        </a>
                      )}
                      {paper.full_text_available && (
                        <span className="text-[10px] text-green-400 font-medium">Full text available</span>
                      )}
                    </div>
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
