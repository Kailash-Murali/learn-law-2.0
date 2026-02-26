"use client"

import type React from "react"
import { Mic, Files, ArrowUp } from "lucide-react"
import { useState, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"

const SUGGESTIONS = [
  "Contract law basics",
  "Tort vs. crime",
  "Constitutional rights overview",
  "Intellectual property 101",
  "What is consideration?",
  "Strict liability examples",
]

export function SearchBar() {
  const router = useRouter()
  const { toast } = useToast()
  const params = useSearchParams()
  const initial = params.get("q") ?? ""

  const [query, setQuery] = useState(initial)
  const [hasAudio, setHasAudio] = useState(false)
  const [filesCount, setFilesCount] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSend()
  }

  function handleCurious() {
    const pick = SUGGESTIONS[Math.floor(Math.random() * SUGGESTIONS.length)]
    setQuery(pick)
    if (inputRef.current) {
      inputRef.current.focus()
    }
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

  const canSend = query.trim().length > 0 || hasAudio || filesCount > 0

  function onSend() {
    if (!canSend) return
    const trimmed = query.trim()
    if (trimmed) {
      router.push(`/?q=${encodeURIComponent(trimmed)}`)
      toast({ title: "Search submitted", description: trimmed })
      return
    }
    if (filesCount > 0) {
      toast({ title: "Files sent", description: `${filesCount} file(s) submitted` })
      return
    }
    if (hasAudio) {
      toast({ title: "Audio sent", description: "Audio input submitted" })
      return
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full" role="search" aria-label="Site search">
      <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={"What do you want to learn today?"}
            aria-label="Search for legal topics"
            className="h-12 w-full bg-background text-foreground placeholder:text-muted-foreground border-border pl-4 pr-28"
          />

          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onAudio}
              className="h-8 w-8 rounded-full text-foreground bg-transparent"
              aria-label="Audio"
              title="Audio"
            >
              <Mic className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Audio</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onFiles}
              className="h-8 w-8 rounded-full text-foreground bg-transparent"
              aria-label="Files"
              title="Files"
            >
              <Files className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Files</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onSend}
              disabled={!canSend}
              className="h-8 w-8 rounded-full text-foreground bg-transparent"
              aria-label="Send"
              title="Send"
            >
              <ArrowUp className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Send</span>
            </Button>
          </div>
        </div>
        <Button
          type="button"
          variant="secondary"
          className="h-12 px-4 whitespace-nowrap w-full sm:w-auto flex-shrink-0"
          onClick={handleCurious}
        >
          {"I'm feeling curious...."}
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
      <button type="submit" className="sr-only">
        Submit search
      </button>
    </form>
  )
}
