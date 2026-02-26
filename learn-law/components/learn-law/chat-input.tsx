"use client"

import type React from "react"
import { Mic, Files, ArrowUp, Square } from "lucide-react"
import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"

const SUGGESTIONS = [
  "Contract law basics",
  "Tort vs. crime",
  "Constitutional rights overview",
  "Intellectual property 101",
  "What is consideration?",
  "Strict liability examples",
]

interface ChatInputProps {
  onSend: (text: string) => void
  isLoading?: boolean
}

export function ChatInput({ onSend, isLoading = false }: ChatInputProps) {
  const { toast } = useToast()
  const [query, setQuery] = useState("")
  const [hasAudio, setHasAudio] = useState(false)
  const [filesCount, setFilesCount] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const canSend = (query.trim().length > 0 || hasAudio || filesCount > 0) && !isLoading

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
    if (trimmed) {
      onSend(trimmed)
      setQuery("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }

  function handleCurious() {
    const pick = SUGGESTIONS[Math.floor(Math.random() * SUGGESTIONS.length)]
    setQuery(pick)
    textareaRef.current?.focus()
  }

  function onAudio() {
    setHasAudio(true)
    toast({ title: "Audio input", description: "Microphone action queued." })
  }

  function onFiles() {
    fileInputRef.current?.click()
  }

  function onFilesChange(e: React.ChangeEvent<HTMLInputElement>) {
    const count = e.target.files?.length ?? 0
    setFilesCount(count)
    toast({
      title: count ? "Files selected" : "No files",
      description: count ? `${count} file(s) ready` : "Choose files to attach.",
    })
  }

  return (
    <div className="w-full rounded-2xl border border-background/20 bg-background/5 shadow-lg shadow-black/20 focus-within:border-background/40 transition-all duration-200">
      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => { setQuery(e.target.value); autoResize() }}
        onKeyDown={handleKeyDown}
        placeholder={isLoading ? "Responding…" : "What do you want to learn today?"}
        disabled={isLoading}
        rows={1}
        aria-label="Chat input"
        className="w-full resize-none bg-transparent text-background placeholder:text-background/30 px-4 pt-4 pb-2 text-sm leading-relaxed outline-none min-h-[52px] max-h-[200px] disabled:opacity-40"
      />

      {/* Toolbar row – never wraps, icons collapse on xs */}
      <div className="flex items-center justify-between px-3 pb-3 pt-1 gap-2 min-w-0">
        {/* Left actions */}
        <div className="flex items-center gap-1 min-w-0 overflow-hidden">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onAudio}
            className="h-8 w-8 shrink-0 rounded-full text-background/50 hover:text-background hover:bg-background/10"
            aria-label="Voice input"
          >
            <Mic className="h-4 w-4" />
          </Button>
          <div className="relative shrink-0">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onFiles}
              className="h-8 w-8 rounded-full text-background/50 hover:text-background hover:bg-background/10"
              aria-label="Attach files"
            >
              <Files className="h-4 w-4" />
            </Button>
            {filesCount > 0 && (
              <span className="absolute -top-1 -right-1 text-[10px] bg-ring text-background rounded-full w-4 h-4 flex items-center justify-center pointer-events-none">
                {filesCount}
              </span>
            )}
          </div>
          {/* Label shortens on mobile */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCurious}
            className="h-8 px-2 sm:px-3 text-xs text-background/50 hover:text-background hover:bg-background/10 rounded-full shrink-0"
          >
            <span className="hidden sm:inline">I&apos;m feeling curious</span>
            <span className="sm:hidden">Curious?</span>
          </Button>
        </div>

        {/* Send / Stop – always rightmost, never pushed */}
        <Button
          type="button"
          size="icon"
          onClick={submit}
          disabled={!canSend && !isLoading}
          className={`h-8 w-8 rounded-full shrink-0 transition-colors
            ${isLoading
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

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={onFilesChange}
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  )
}
