"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { User, Plus, MessageSquare, Pencil, Trash2, Check, X } from "lucide-react"
import Link from "next/link"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet"
import type { ChatSession } from "@/app/page"

interface CornerIconsProps {
  chatMode?: boolean
  sessions?: ChatSession[]
  activeSessionId?: string | null
  onLoadSession?: (session: ChatSession) => void
  onNewChat?: () => void
  onRenameSession?: (id: string, newTitle: string) => void
  onDeleteSession?: (id: string) => void
}

function SessionItem({
  session,
  isActive,
  onLoad,
  onRename,
  onDelete,
}: {
  session: ChatSession
  isActive: boolean
  onLoad: () => void
  onRename: (newTitle: string) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(session.title)
  const [hovered, setHovered] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  function commitRename() {
    onRename(draft)
    setEditing(false)
  }

  function cancelRename() {
    setDraft(session.title)
    setEditing(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") commitRename()
    if (e.key === "Escape") cancelRename()
  }

  return (
    <div
      className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 transition-colors
        ${isActive ? "bg-background/15 text-background" : "text-background/70 hover:bg-background/10 hover:text-background"}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <MessageSquare className="size-3.5 shrink-0 text-background/40 mr-1" />

      {editing ? (
        /* ── Inline rename input ── */
        <div className="flex flex-1 items-center gap-1 min-w-0">
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 min-w-0 bg-background/10 text-background text-xs rounded px-1.5 py-0.5 outline-none border border-background/20 focus:border-background/50"
          />
          <button
            onClick={commitRename}
            className="shrink-0 text-background/60 hover:text-background p-0.5 rounded"
            aria-label="Confirm rename"
          >
            <Check className="size-3.5" />
          </button>
          <button
            onClick={cancelRename}
            className="shrink-0 text-background/60 hover:text-background p-0.5 rounded"
            aria-label="Cancel rename"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ) : (
        /* ── Normal row ── */
        <>
          <button
            onClick={onLoad}
            className="flex-1 text-left text-xs truncate min-w-0"
            title={session.title}
          >
            {session.title}
          </button>

          {/* Action icons – visible on hover or when active */}
          <div className={`flex items-center gap-0.5 shrink-0 transition-opacity ${hovered || isActive ? "opacity-100" : "opacity-0"}`}>
            <button
              onClick={(e) => { e.stopPropagation(); setEditing(true) }}
              className="p-1 rounded text-background/50 hover:text-background hover:bg-background/10"
              aria-label="Rename chat"
            >
              <Pencil className="size-3" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete() }}
              className="p-1 rounded text-background/50 hover:text-red-400 hover:bg-background/10"
              aria-label="Delete chat"
            >
              <Trash2 className="size-3" />
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export function CornerIcons({
  chatMode = false,
  sessions = [],
  activeSessionId = null,
  onLoadSession,
  onNewChat,
  onRenameSession,
  onDeleteSession,
}: CornerIconsProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full hover:bg-background/10 focus-visible:ring-0 focus-visible:outline-none"
          aria-label="Open sidebar"
        >
          <User className="size-4 text-background" aria-hidden />
          <span className="sr-only">Open sidebar</span>
        </Button>
      </SheetTrigger>

      <SheetContent
        side="left"
        className="w-72 sm:max-w-xs bg-foreground text-background flex flex-col p-0 border-r border-border/20"
      >
        <SheetHeader className="px-4 pt-5 pb-3 border-b border-border/20">
          <SheetTitle className="text-background text-base font-semibold">Learn Law</SheetTitle>
          <SheetDescription className="sr-only">Chat history and navigation</SheetDescription>
        </SheetHeader>

        {/* New chat */}
        <div className="px-3 py-3 border-b border-border/20">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-background/80 hover:text-background hover:bg-background/10 rounded-lg h-9 text-sm"
            onClick={onNewChat}
          >
            <Plus className="size-4 shrink-0" />
            New chat
          </Button>
        </div>

        {/* Chat history */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {sessions.length === 0 ? (
            <p className="text-xs text-background/40 px-2 py-2">No chats yet. Start one!</p>
          ) : (
            <div className="space-y-0.5">
              <p className="text-xs text-background/40 uppercase tracking-wider px-2 pb-2">Recent chats</p>
              {sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={session.id === activeSessionId}
                  onLoad={() => onLoadSession?.(session)}
                  onRename={(newTitle) => onRenameSession?.(session.id, newTitle)}
                  onDelete={() => onDeleteSession?.(session.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer – Settings only */}
        <div className="border-t border-border/20 px-3 py-3">
          <Link
            href="/settings"
            className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-background/70 hover:text-background hover:bg-background/10 transition-colors"
          >
            Settings
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default CornerIcons
