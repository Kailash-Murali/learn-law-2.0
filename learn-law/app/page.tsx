"use client"

import { useState, useRef, useEffect } from "react"
import { CornerIcons } from "@/components/learn-law/corner-icons"
import { Hero } from "@/components/learn-law/hero"
import { ChatInput } from "@/components/learn-law/chat-input"
import { ValidationPanel, type ValidationData } from "@/components/learn-law/validation-panel"
import { SpringerPapersPanel } from "@/components/learn-law/springer-papers-panel"
import { ContrastivePanel } from "@/components/learn-law/contrastive-panel"
import { Scale, Copy, Check, ThumbsUp, ThumbsDown, Pencil, Download, FileDown } from "lucide-react"
import { AboutPopover } from "@/components/learn-law/about-popover"
import { SentenceHighlighter } from "@/components/learn-law/sentence-highlighter"

export interface Message {
  id: string
  role: "user" | "assistant"
  text: string
  mode?: string | null
  draftType?: string | null
  pdfPath?: string | null
  docxPath?: string | null
  uiPayload?: Record<string, any> | null
  contrastive?: Record<string, any> | null
  queryType?: string | null
  diceFeatures?: Record<string, unknown> | null
  userQuery?: string | null
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

// ── Thinking indicator ────────────────────────────────────────────────────────
function ThinkingIndicator() {
  return (
    <div className="flex justify-start" aria-label="Loading response" aria-busy="true">
      <Scale className="size-4 mt-1 mr-2 shrink-0 text-background/60 animate-pulse" aria-hidden />
      <div className="rounded-2xl rounded-bl-sm bg-background/10 px-4 py-3">
        <span className="text-sm text-background/60 font-medium">Thinking</span>
      </div>
    </div>
  )
}

// ── Typewriter text ──────────────────────────────────────────────────────────
function TypewriterText({ text, speed = 8, onDone }: { text: string; speed?: number; onDone?: () => void }) {
  const [displayed, setDisplayed] = useState("")
  const [done, setDone] = useState(false)
  const onDoneRef = useRef(onDone)
  useEffect(() => { onDoneRef.current = onDone }, [onDone])

  useEffect(() => {
    setDisplayed("")
    setDone(false)
    let i = 0
    const id = setInterval(() => {
      // Reveal multiple characters per tick for long texts
      const chunk = Math.max(1, Math.floor(text.length / 300))
      i = Math.min(i + chunk, text.length)
      setDisplayed(text.slice(0, i))
      if (i >= text.length) {
        clearInterval(id)
        setDone(true)
        onDoneRef.current?.()
      }
    }, speed)
    return () => clearInterval(id)
  }, [text, speed])

  return <>{done ? text : displayed}</>
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
    contrastive: Record<string, any> | null
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

    return {
      text: mainText,
      uiPayload: ui ?? null,
      contrastive: (ui?.contrastive as Record<string, any>) ?? null,
    }
  }

  // ── State ────────────────────────────────────────────────
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [thinking, setThinking] = useState(false)
  const [feedbackLog, setFeedbackLog] = useState<Record<string, FeedbackEntry>>({})
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState("")
  const [newMsgId, setNewMsgId] = useState<string | null>(null)
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set())
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
        const { text: respText, uiPayload, contrastive } = formatBackendResponse(data)
        const asstId = (Date.now() + 1).toString()
        setNewMsgId(asstId)
        const assistantMsg: Message = {
          id: asstId,
          role: "assistant",
          text: respText,
          mode,
          draftType,
          pdfPath: data.pdf_path ?? null,
          docxPath: data.docx_path ?? null,
          uiPayload,
          contrastive,
          queryType: uiPayload?.query_type ?? null,
          diceFeatures: uiPayload?.dice_features ?? null,
          userQuery: queryText,
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
    // Truncate everything after this message so the new response replaces the old
    const updated = [...messages.slice(0, idx), updatedMsg]
    setMessages(updated)
    setEditingId(null)
    const sid = sessionIdRef.current
    if (sid) {
      setSessions((prev) =>
        prev.map((s) => s.id === sid ? { ...s, messages: updated } : s)
      )
      callApi(newText, updated, sid)
    }
  }

  async function handleFeedback(id: string, entry: FeedbackEntry) {
    setFeedbackLog((prev) => ({ ...prev, [id]: entry }))
    const idx = messages.findIndex((m) => m.id === id)
    const query = idx > 0 ? (messages[idx - 1]?.text ?? null) : null
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: id,
          vote: entry.vote,
          comment: entry.comment ?? null,
          query,
        }),
      })
    } catch {
      // silent — feedback failure must not disrupt the UX
    }
  }

  function loadSession(session: ChatSession) {
    setActiveSessionId(session.id)
    setMessages(session.messages)
    setThinking(false)
    setNewMsgId(null)
    // All loaded messages are pre-revealed
    setRevealedIds(new Set(session.messages.map((m) => m.id)))
  }

  function startNewChat() {
    setActiveSessionId(null)
    setMessages([])
    setThinking(false)
    setNewMsgId(null)
    setRevealedIds(new Set())
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
      <div className="flex-1 overflow-y-auto scrollbar-page">
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
            {messages.map((msg, msgIdx) => {
              const isLastUserMsg = msg.role === "user" && !messages.slice(msgIdx + 1).some((m) => m.role === "user")
              return (
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
                    {isLastUserMsg && editingId === msg.id ? (
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
                        {isLastUserMsg && (
                        <button
                          onClick={() => { setEditingId(msg.id); setEditText(msg.text) }}
                          aria-label="Edit message"
                          className="opacity-0 group-hover:opacity-100 transition-opacity mt-2.5 p-1 rounded text-background/30 hover:text-background/60 shrink-0 cursor-pointer"
                        >
                          <Pencil className="size-3.5" aria-hidden />
                        </button>
                        )}
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
                        {msg.id === newMsgId
                          ? <TypewriterText text={msg.text} onDone={() => setRevealedIds((prev) => new Set([...prev, msg.id]))} />
                          : <SentenceHighlighter
                              text={msg.text}
                              citations={(
                                msg.uiPayload?.validation as { citations?: { name: string; url?: string | null; verified?: boolean }[] } | undefined
                              )?.citations}
                            />}
                      </div>
                      {/* Copy button – top-right corner, visible on hover */}
                      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <CopyButton text={msg.text} />
                      </div>
                    </div>
                    {/* Mode-specific actions and panels — revealed only after typewriter finishes */}
                    {(revealedIds.has(msg.id) || msg.id !== newMsgId) && (
                      <>
                        {msg.mode === "[draft]" && <DraftActions text={msg.text} docxPath={msg.docxPath} />}
                        {msg.mode === "[research]" && <ReportActions text={msg.text} pdfPath={msg.pdfPath} />}
                        {(msg.mode === "[contrastive]" || msg.uiPayload?.query_type === "classification") && (
                          <ContrastivePanel
                            data={msg.contrastive}
                            queryType={msg.queryType ?? "advisory"}
                            diceFeatures={msg.diceFeatures}
                            userQuery={msg.userQuery ?? undefined}
                          />
                        )}
                        {msg.uiPayload?.validation && (
                          <ValidationPanel
                            validation={msg.uiPayload.validation as ValidationData}
                          />
                        )}
                        {Array.isArray(msg.uiPayload?.springer_papers) && msg.uiPayload.springer_papers.length > 0 && (
                          <SpringerPapersPanel papers={msg.uiPayload.springer_papers} />
                        )}
                      </>
                    )}
                    <ThumbsFeedback
                      messageId={msg.id}
                      onSubmit={handleFeedback}
                    />
                  </div>
                )}
              </div>
              )
            })}
            {thinking && <ThinkingIndicator />}
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

