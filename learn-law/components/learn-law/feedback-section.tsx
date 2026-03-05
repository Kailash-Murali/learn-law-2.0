"use client"

import { useState } from "react"
import { Copy, Check, MessageSquareWarning } from "lucide-react"
import { cn } from "@/lib/utils"

interface FeedbackSectionProps {
  feedbackId: string
  className?: string
}

export function FeedbackSection({ feedbackId, className }: FeedbackSectionProps) {
  const [copied, setCopied] = useState(false)

  if (!feedbackId) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(feedbackId)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for non-secure contexts
      const el = document.createElement("textarea")
      el.value = feedbackId
      el.style.position = "fixed"
      el.style.opacity = "0"
      document.body.appendChild(el)
      el.select()
      document.execCommand("copy")
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-lg border border-background/10 px-3 py-2",
        className
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        <MessageSquareWarning className="size-3.5 shrink-0 text-background/30" aria-hidden />
        <span className="text-[11px] text-background/40 truncate">
          ID: <span className="font-mono text-background/50">{feedbackId}</span>
        </span>
      </div>
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 text-[11px] text-background/40 hover:text-background/60 transition-colors shrink-0 cursor-pointer"
        title="Copy feedback ID"
      >
        {copied ? (
          <>
            <Check className="size-3 text-green-400" aria-hidden />
            <span className="text-green-400">Copied</span>
          </>
        ) : (
          <>
            <Copy className="size-3" aria-hidden />
            <span>Copy</span>
          </>
        )}
      </button>
    </div>
  )
}
