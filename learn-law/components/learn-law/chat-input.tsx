"use client"

import type React from "react"
import { ArrowUp, Square } from "lucide-react"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"

const MODES = [
  { label: "Research", tag: "[research]" },
  { label: "Draft",    tag: "[draft]" },
] as const

const DRAFT_TYPES = [
  { label: "Writ Petition",  value: "writ_petition" },
  { label: "Legal Notice",   value: "legal_notice" },
  { label: "RTI Application", value: "rti" },
  { label: "Complaint",      value: "complaint" },
  { label: "Affidavit",      value: "affidavit" },
  { label: "PIL",            value: "pil" },
] as const

type ModeTag = (typeof MODES)[number]["tag"] | null

interface ChatInputProps {
  onSend: (text: string, mode: string | null, draftType?: string | null) => void
  isLoading?: boolean
}

export function ChatInput({ onSend, isLoading = false }: ChatInputProps) {
  const [query, setQuery] = useState("")
  const [activeMode, setActiveMode] = useState<ModeTag>(null)
  const [activeDraftType, setActiveDraftType] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canSend = query.trim().length > 0 && !isLoading

  // Reset draft type when mode changes away from [draft]
  useEffect(() => {
    if (activeMode !== "[draft]") setActiveDraftType(null)
  }, [activeMode])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    if (!canSend) return
    const trimmed = query.trim()
    if (!trimmed) return
    onSend(trimmed, activeMode, activeDraftType)
    setQuery("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"
  }

  return (
    <div className="w-full rounded-2xl border border-background/20 bg-background/5 shadow-lg shadow-black/20 focus-within:border-background/40 transition-all duration-200">
      {/* ── Textarea ── */}
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => { setQuery(e.target.value); autoResize() }}
        onKeyDown={handleKeyDown}
        placeholder={isLoading ? "Responding…" : "What do you want to learn today?"}
        disabled={isLoading}
        rows={1}
        aria-label="Chat input"
        className="w-full resize-none bg-transparent text-background placeholder:text-background/30 px-4 pt-2 pb-1 text-sm leading-relaxed outline-none min-h-[52px] max-h-[200px] disabled:opacity-40"
      />

      {/* ── Draft sub-menu (only when Draft mode is active) ── */}
      {activeMode === "[draft]" && (
        <div className="flex items-center gap-1.5 px-3 pb-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {DRAFT_TYPES.map((dt) => (
            <button
              key={dt.value}
              type="button"
              onClick={() => setActiveDraftType(activeDraftType === dt.value ? null : dt.value)}
              aria-label={`Draft type: ${dt.label}`}
              aria-pressed={activeDraftType === dt.value}
              className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
                activeDraftType === dt.value
                  ? "bg-background/80 text-foreground"
                  : "bg-background/5 text-background/40 hover:bg-background/10 hover:text-background/60 border border-background/10"
              }`}
            >
              {dt.label}
            </button>
          ))}
        </div>
      )}

      {/* ── Toolbar: chips left, send right ── */}
      <div className="flex items-center justify-between px-3 pb-2 pt-0.5 gap-2">
        {/* Mode chips */}
        <div
          className="flex items-center gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden min-w-0"
          role="group"
          aria-label="Query mode"
        >
          {MODES.map((m) => (
            <button
              key={m.tag}
              type="button"
              onClick={() => setActiveMode(activeMode === m.tag ? null : m.tag)}
              aria-label={`Mode: ${m.label}`}
              aria-pressed={activeMode === m.tag}
              className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer ${
                activeMode === m.tag
                  ? "bg-background text-foreground"
                  : "bg-background/10 text-background/60 hover:bg-background/20 hover:text-background/80"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Send / Stop */}
        <Button
          type="button"
          size="icon"
          onClick={submit}
          disabled={!canSend && !isLoading}
          className={`h-8 w-8 rounded-full shrink-0 transition-colors ${
            isLoading
              ? "bg-red-500 hover:bg-red-600 text-white"
              : canSend
              ? "bg-background text-foreground hover:bg-background/90"
              : "bg-background/15 text-background/30 cursor-not-allowed"
          }`}
          aria-label={isLoading ? "Stop" : "Send"}
        >
          {isLoading ? <Square className="h-3 w-3 fill-current" /> : <ArrowUp className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
}
