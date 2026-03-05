"use client"

import type React from "react"
import { ArrowUp } from "lucide-react"
import { useState, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function SearchBar() {
  const router = useRouter()
  const params = useSearchParams()
  const initial = params.get("q") ?? ""

  const [query, setQuery] = useState(initial)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSend()
  }

  const canSend = query.trim().length > 0

  function onSend() {
    if (!canSend) return
    router.push(`/?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full" role="search" aria-label="Site search">
      <div className="relative w-full">
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What do you want to learn today?"
          aria-label="Search for legal topics"
          className="h-12 w-full bg-background text-foreground placeholder:text-muted-foreground border-border pl-4 pr-14"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <Button
            type="submit"
            variant="outline"
            size="icon"
            disabled={!canSend}
            className="h-8 w-8 rounded-full text-foreground bg-transparent"
            aria-label="Send"
          >
            <ArrowUp className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Send</span>
          </Button>
        </div>
      </div>
    </form>
  )
}
