"use client"

import { useState, useRef, useEffect } from "react"
import { CornerIcons } from "@/components/learn-law/corner-icons"
import { Hero } from "@/components/learn-law/hero"
import { ChatInput } from "@/components/learn-law/chat-input"
import { ValidationPanel, type ValidationData } from "@/components/learn-law/validation-panel"
import { Scale, Copy, Check, ThumbsUp, ThumbsDown, Pencil, Download, FileDown } from "lucide-react"
import { AboutPopover } from "@/components/learn-law/about-popover"

export interface Message {
  id: string
  role: "user" | "assistant"
  text: string
  mode?: string | null
  draftType?: string | null
  pdfPath?: string | null
  docxPath?: string | null
  uiPayload?: Record<string, any> | null
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

// ── Skeleton shimmer ─────────────────────────────────────────────────────────
function MessageSkeleton() {
  return (
    <div className="flex justify-start" aria-label="Loading response" aria-busy="true">
      <Scale className="size-4 mt-1 mr-2 shrink-0 text-background/60 animate-pulse" aria-hidden />
      <div className="max-w-[78%] w-64 space-y-2.5 pt-1">
        <div className="h-3.5 w-2/5 rounded-full bg-background/15 animate-pulse" />
        <div className="h-3 w-full rounded-full bg-background/10 animate-pulse" />
        <div className="h-3 w-4/5 rounded-full bg-background/10 animate-pulse" />
        <div className="h-3 w-3/5 rounded-full bg-background/10 animate-pulse" />
      </div>
    </div>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const el = document.createElement("textarea")
      el.value = text
      el.style.cssText = "position:fixed;opacity:0"
      document.body.appendChild(el)
      el.select()
      document.execCommand("copy")
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      aria-label="Copy response"
      className="p-1 rounded text-background/30 hover:text-background/60 transition-colors cursor-pointer"
    >
      {copied
        ? <Check className="size-3.5 text-green-400" aria-hidden />
        : <Copy className="size-3.5" aria-hidden />
      }
    </button>
  )
}

// ── Draft mode actions ────────────────────────────────────────────────────────
function DraftActions({ text, docxPath }: { text: string; docxPath?: string | null }) {
  function handleDownload() {
    if (docxPath) {
      window.open(`/api/download?path=${encodeURIComponent(docxPath)}`, "_blank")
    } else {
      const blob = new Blob([text], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "draft.txt"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  return (
    <div className="flex items-center gap-1 mt-1.5">
      <CopyButton text={text} />
      <button
        onClick={handleDownload}
        aria-label={docxPath ? "Download draft as Word" : "Download draft"}
        className="p-1 rounded text-background/30 hover:text-background/60 transition-colors cursor-pointer"
      >
        <Download className="size-3.5" aria-hidden />
      </button>
    </div>
  )
}

// ── Reports mode actions ──────────────────────────────────────────────────────
function ReportActions({ text, pdfPath }: { text: string; pdfPath?: string | null }) {
  function handleDownload() {
    if (pdfPath) {
      window.open(`/api/download?path=${encodeURIComponent(pdfPath)}`, "_blank")
    } else {
      const blob = new Blob([text], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "report.txt"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  return (
    <div className="flex items-center gap-1 mt-1.5">
      <button
        onClick={handleDownload}
        aria-label={pdfPath ? "Download report as PDF" : "Download report"}
        className="p-1 rounded text-background/30 hover:text-background/60 transition-colors cursor-pointer"
      >
        <FileDown className="size-3.5" aria-hidden />
      </button>
    </div>
  )
}

// ── Thumbs feedback ───────────────────────────────────────────────────────────
type FeedbackEntry = { vote: "up" | "down"; comment?: string }

function ThumbsFeedback({
  messageId,
  onSubmit,
}: {
  messageId: string
  onSubmit: (id: string, entry: FeedbackEntry) => void
}) {
  const [vote, setVote] = useState<"up" | "down" | null>(null)
  const [comment, setComment] = useState("")
  const [submitted, setSubmitted] = useState(false)

  function handleUp() {
    if (vote !== null) return
    setVote("up")
    onSubmit(messageId, { vote: "up" })
    setSubmitted(true)
  }

  function handleDown() {
    if (vote !== null) return
    setVote("down")
  }

  function submitComment() {
    onSubmit(messageId, { vote: "down", comment: comment.trim() || undefined })
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <p className="mt-1.5 text-[11px] text-background/40 select-none">
        {vote === "up" ? "Thanks — glad that was helpful!" : "Thanks for the feedback, we'll use it to improve."}
      </p>
    )
  }

  return (
    <div className="mt-1.5 space-y-1.5">
      {/* Thumb buttons */}
      <div className="flex items-center gap-1" role="group" aria-label="Rate this response">
        <button
          onClick={handleUp}
          disabled={vote !== null}
          aria-label="Thumbs up"
          aria-pressed={vote === "up"}
          className={`p-1 rounded transition-colors cursor-pointer disabled:cursor-default ${
            vote === "up"
              ? "text-green-400"
              : vote !== null
              ? "text-background/20"
              : "text-background/30 hover:text-background/60"
          }`}
        >
          <ThumbsUp className="size-3.5" aria-hidden />
        </button>
        <button
          onClick={handleDown}
          disabled={vote !== null}
          aria-label="Thumbs down"
          aria-pressed={vote === "down"}
          className={`p-1 rounded transition-colors cursor-pointer disabled:cursor-default ${
            vote === "down"
              ? "text-red-400"
              : vote !== null
              ? "text-background/20"
              : "text-background/30 hover:text-background/60"
          }`}
        >
          <ThumbsDown className="size-3.5" aria-hidden />
        </button>
      </div>

      {/* Grievance input — only shown after thumbs down */}
      {vote === "down" && (
        <div className="rounded-xl border border-background/15 bg-background/5 px-3 py-2 space-y-2">
          <label
            htmlFor={`feedback-${messageId}`}
            className="block text-[11px] text-background/50"
          >
            What could be better?
          </label>
          <textarea
            id={`feedback-${messageId}`}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Tell us what went wrong…"
            rows={2}
            autoFocus
            aria-label="Describe your feedback"
            className="w-full resize-none bg-transparent text-background/80 placeholder:text-background/25 text-xs leading-relaxed outline-none"
          />
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={() => { setVote(null) }}
              aria-label="Cancel feedback"
              className="text-[11px] text-background/35 hover:text-background/60 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={submitComment}
              aria-label="Submit feedback"
              className="rounded-full bg-background/15 hover:bg-background/25 text-background/70 hover:text-background text-[11px] px-3 py-1 transition-colors cursor-pointer"
            >
              Submit
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Page() {
  // ── Helpers ──────────────────────────────────────────────
  /** Extract main content text and structured ui payload from backend response. */
  function formatBackendResponse(data: Record<string, any>): {
    text: string
    uiPayload: Record<string, any> | null
  } {
    const ui = data.ui_payload as Record<string, any> | undefined
    const doc = data.documentation as Record<string, any> | undefined

    // Primary content only — validation is rendered as rich components
    const mainText =
      ui?.content ??
      doc?.answer ??
      doc?.draft ??
      doc?.executive_summary ??
      data.error ??
      "No results returned."

    return { text: mainText, uiPayload: ui ?? null }
  }

  // ── State ────────────────────────────────────────────────
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [thinking, setThinking] = useState(false)
  const [feedbackLog, setFeedbackLog] = useState<Record<string, FeedbackEntry>>({})
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState("")
  const isChat = messages.length > 0 || thinking
  const bottomRef = useRef<HTMLDivElement>(null)
  // Use a ref so the setTimeout closure always has the latest session id
  const sessionIdRef = useRef<string | null>(null)

  useEffect(() => {
    sessionIdRef.current = activeSessionId
  }, [activeSessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, thinking])

  // ── Shared API call ──────────────────────────────────────
  function callApi(queryText: string, priorMessages: Message[], sid: string, mode: string | null = null, draftType: string | null = null) {
    setThinking(true)
    fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, mode: mode ?? null, draft_type: draftType ?? null }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: res.statusText }))
          throw new Error(err.error ?? "Research request failed")
        }
        return res.json()
      })
      .then((data) => {
        setThinking(false)
        const { text: respText, uiPayload } = formatBackendResponse(data)
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: respText,
          mode,
          draftType,
          pdfPath: data.pdf_path ?? null,
          docxPath: data.docx_path ?? null,
          uiPayload,
        }
        const finalMessages = [...priorMessages, assistantMsg]
        setMessages(finalMessages)
        setSessions((prev) =>
          prev.map((s) => s.id === sid ? { ...s, messages: finalMessages } : s)
        )
      })
      .catch((err) => {
        setThinking(false)
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: `⚠ ${err.message ?? "Something went wrong. Is the backend running?"}`,
        }
        const finalMessages = [...priorMessages, assistantMsg]
        setMessages(finalMessages)
        setSessions((prev) =>
          prev.map((s) => s.id === sid ? { ...s, messages: finalMessages } : s)
        )
      })
  }

  function handleSend(text: string, mode: string | null = null, draftType: string | null = null) {
    const userMsg: Message = { id: Date.now().toString(), role: "user", text, mode, draftType }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)

    // Create a new session on first message, else update existing
    let currentSessionId = sessionIdRef.current
    if (!currentSessionId) {
      const newId = Date.now().toString()
      const newSession: ChatSession = {
        id: newId,
        title: text.length > 45 ? text.slice(0, 45) + "…" : text,
        messages: updatedMessages,
        createdAt: new Date(),
      }
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(newId)
      sessionIdRef.current = newId
      currentSessionId = newId
    } else {
      setSessions((prev) =>
        prev.map((s) => s.id === currentSessionId ? { ...s, messages: updatedMessages } : s)
      )
    }

    callApi(text, updatedMessages, currentSessionId, mode, draftType)
  }

  function handleResend(msgId: string, newText: string) {
    const idx = messages.findIndex((m) => m.id === msgId)
    if (idx === -1) return
    const updatedMsg: Message = { ...messages[idx], text: newText }
    const truncated = [...messages.slice(0, idx), updatedMsg]
    setMessages(truncated)
    setEditingId(null)
    const sid = sessionIdRef.current
    if (sid) {
      setSessions((prev) =>
        prev.map((s) => s.id === sid ? { ...s, messages: truncated } : s)
      )
      callApi(newText, truncated, sid)
    }
  }

  function handleFeedback(id: string, entry: FeedbackEntry) {
    setFeedbackLog((prev) => ({ ...prev, [id]: entry }))
    // Future: POST /api/feedback with { messageId: id, ...entry }
  }

  function loadSession(session: ChatSession) {
    setActiveSessionId(session.id)
    setMessages(session.messages)
    setThinking(false)
  }

  function startNewChat() {
    setActiveSessionId(null)
    setMessages([])
    setThinking(false)
    sessionIdRef.current = null
  }

  function renameSession(id: string, newTitle: string) {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle.trim() || s.title } : s))
    )
  }

  function deleteSession(id: string) {
    setSessions((prev) => prev.filter((s) => s.id !== id))
    // If the deleted session was active, reset to landing
    if (sessionIdRef.current === id) {
      setActiveSessionId(null)
      setMessages([])
      setThinking(false)
      sessionIdRef.current = null
    }
  }

  return (
    <main className="min-h-dvh bg-foreground text-background flex flex-col overflow-x-hidden">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-10 flex w-full items-center justify-between px-4 py-2 border-b border-border/20 bg-foreground">
        {/* Left: sidebar icon + about link */}
        <div className="flex items-center gap-2">
          <CornerIcons
            chatMode={isChat}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onLoadSession={loadSession}
            onNewChat={startNewChat}
            onRenameSession={renameSession}
            onDeleteSession={deleteSession}
          />
          <AboutPopover />
        </div>
        {/* Right: Scale logo + title */}
        <div className="flex items-center gap-3">
          {isChat && (
            <span className="text-sm font-medium text-background/70">
              அறம்
            </span>
          )}
          <Scale className="size-5 text-background" aria-hidden />
        </div>
      </div>

      {/* ── Hero (landing) or Chat messages ── */}
      <div className="flex-1 overflow-y-auto">
        {!isChat ? (
          /* Landing – hero + input centred together vertically */
          <section className="flex flex-col items-center justify-center min-h-[calc(100dvh-49px)] w-full px-4 sm:px-8">
            <div className="w-full max-w-[min(860px,100%)] space-y-6">
              <Hero />
              <ChatInput onSend={handleSend} isLoading={thinking} />
            </div>
          </section>
        ) : (
          <section className="mx-auto w-full max-w-[min(860px,100%)] px-4 sm:px-8 py-6 flex flex-col gap-2 sm:gap-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <Scale className="size-4 mt-1 mr-2 shrink-0 text-background/60" aria-hidden />
                )}

                {msg.role === "user" ? (
                  /* ── User bubble ── */
                  <div className="max-w-[85%] sm:max-w-[88%] group">
                    {editingId === msg.id ? (
                      /* Edit mode */
                      <div className="rounded-2xl rounded-br-sm bg-background/10 px-4 py-3 space-y-2">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          autoFocus
                          rows={3}
                          aria-label="Edit message"
                          className="w-full resize-none bg-transparent text-background text-sm leading-relaxed outline-none"
                        />
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => setEditingId(null)}
                            aria-label="Cancel edit"
                            className="text-xs text-background/40 hover:text-background/70 transition-colors cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleResend(msg.id, editText.trim())}
                            disabled={!editText.trim()}
                            aria-label="Re-send message"
                            className="rounded-full bg-background text-foreground text-xs px-3 py-1 font-medium hover:bg-background/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                          >
                            Re-send
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Display mode */
                      <div className="relative flex items-start gap-1.5">
                        <button
                          onClick={() => { setEditingId(msg.id); setEditText(msg.text) }}
                          aria-label="Edit message"
                          className="opacity-0 group-hover:opacity-100 transition-opacity mt-2.5 p-1 rounded text-background/30 hover:text-background/60 shrink-0 cursor-pointer"
                        >
                          <Pencil className="size-3.5" aria-hidden />
                        </button>
                        <div className="rounded-2xl rounded-br-sm bg-background text-foreground px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
                          {msg.text}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* ── Assistant bubble ── */
                  <div className="w-full flex flex-col group">
                    <div className="relative">
                      <div className="rounded-2xl rounded-bl-sm bg-background/10 text-background px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.text}
                      </div>
                      {/* Copy button – top-right corner, visible on hover */}
                      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <CopyButton text={msg.text} />
                      </div>
                    </div>
                    {/* Mode-specific actions */}
                    {msg.mode === "[draft]" && <DraftActions text={msg.text} docxPath={msg.docxPath} />}
                    {msg.mode === "[reports]" && <ReportActions text={msg.text} pdfPath={msg.pdfPath} />}
                    {msg.uiPayload?.validation && (
                      <ValidationPanel
                        validation={msg.uiPayload.validation as ValidationData}
                      />
                    )}
                    <ThumbsFeedback
                      messageId={msg.id}
                      onSubmit={handleFeedback}
                    />
                  </div>
                )}
              </div>
            ))}
            {thinking && <MessageSkeleton />}
            <div ref={bottomRef} />
          </section>
        )}
      </div>

      {/* ── Input bar – only shown pinned to bottom in chat mode ── */}
      {isChat && (
        <div className="sticky bottom-0 w-full bg-foreground border-t border-border/20 py-3 px-4 sm:px-8">
          <div className="mx-auto w-full max-w-[min(860px,100%)]">
            <ChatInput onSend={handleSend} isLoading={thinking} />
          </div>
        </div>
      )}
    </main>
  )
}

