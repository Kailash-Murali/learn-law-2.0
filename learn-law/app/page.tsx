"use client"

import { useState, useRef, useEffect } from "react"
import { CornerIcons } from "@/components/learn-law/corner-icons"
import { Hero } from "@/components/learn-law/hero"
import { ChatInput } from "@/components/learn-law/chat-input"
import { Footer } from "@/components/learn-law/footer"
import { Scale } from "lucide-react"

export interface Message {
  id: string
  role: "user" | "assistant"
  text: string
  uiPayload?: Record<string, any> | null
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

export default function Page() {
  // ── Helpers ──────────────────────────────────────────────
  /** Build a nicely formatted text from the backend ui_payload + documentation. */
  function formatBackendResponse(data: Record<string, any>): {
    text: string
    uiPayload: Record<string, any> | null
  } {
    const ui = data.ui_payload as Record<string, any> | undefined
    const doc = data.documentation as Record<string, any> | undefined

    // Primary content: prefer ui_payload.content, then documentation fields
    let mainText =
      ui?.content ??
      doc?.answer ??
      doc?.draft ??
      doc?.executive_summary ??
      data.error ??
      "No results returned."

    const sections: string[] = [mainText]

    // — Validation badges from ui_payload —
    if (ui?.validation) {
      const v = ui.validation

      // Risk badge
      if (v.risk_label) {
        const riskEmoji =
          v.risk_label === "low" ? "🟢" : v.risk_label === "medium" ? "🟡" : "🔴"
        sections.push(`\n${riskEmoji} Confidence: ${v.risk_label.toUpperCase()} (risk score ${v.risk_score ?? "?"})`)
      }

      // Citations
      if (v.citations && v.citations.length > 0) {
        sections.push("\n📚 Case Citations:")
        for (const c of v.citations) {
          const badge = c.ik_verified ? "✅" : "⚠️"
          const link = c.ik_link ? ` — ${c.ik_link}` : ""
          sections.push(`  ${badge} ${c.citation}${link}`)
        }
      }

      // Statutes
      if (v.statutes && v.statutes.length > 0) {
        sections.push("\n📜 Statutes Referenced:")
        for (const s of v.statutes) {
          const badge = s.ik_verified ? "✅" : "⚠️"
          const link = s.ik_link ? ` — ${s.ik_link}` : ""
          sections.push(`  ${badge} ${s.statute}${link}`)
        }
      }

      // Bad laws warnings
      if (v.bad_laws && v.bad_laws.length > 0) {
        sections.push("\n⛔ Repealed / Unconstitutional Laws Detected:")
        for (const b of v.bad_laws) {
          sections.push(`  🚫 ${b.law} — ${b.reason}`)
        }
      }

      // Flags
      if (v.flags && v.flags.length > 0) {
        sections.push("\n⚠️ Flags:")
        for (const f of v.flags) {
          sections.push(`  • ${f}`)
        }
      }
    }

    return { text: sections.join("\n"), uiPayload: ui ?? null }
  }

  // ── State ────────────────────────────────────────────────
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [thinking, setThinking] = useState(false)
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

  function handleSend(text: string) {
    const userMsg: Message = { id: Date.now().toString(), role: "user", text }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setThinking(true)

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

    const sid = currentSessionId

    // Call the backend API
    fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text }),
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
        const { text, uiPayload } = formatBackendResponse(data)
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text,
          uiPayload,
        }
        const finalMessages = [...updatedMessages, assistantMsg]
        setMessages(finalMessages)
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sid ? { ...s, messages: finalMessages } : s,
          ),
        )
      })
      .catch((err) => {
        setThinking(false)
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: `⚠ ${err.message ?? "Something went wrong. Is the backend running?"}`,
        }
        const finalMessages = [...updatedMessages, assistantMsg]
        setMessages(finalMessages)
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sid ? { ...s, messages: finalMessages } : s,
          ),
        )
      })
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
    <main className="min-h-dvh bg-foreground text-background flex flex-col">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-10 flex w-full items-center justify-between px-4 py-2 border-b border-border/20 bg-foreground">
        {/* Left: User / sidebar icon */}
        <CornerIcons
          chatMode={isChat}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onLoadSession={loadSession}
          onNewChat={startNewChat}
          onRenameSession={renameSession}
          onDeleteSession={deleteSession}
        />
        {/* Right: Scale logo + title */}
        <div className="flex items-center gap-2">
          {isChat && (
            <span className="text-sm font-medium text-background/70">
              Learn Law
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
            <div className="w-full max-w-[min(680px,100%)] space-y-6">
              <Hero />
              <ChatInput onSend={handleSend} isLoading={thinking} />
            </div>
          </section>
        ) : (
          <section className="mx-auto w-full max-w-[min(680px,100%)] px-4 sm:px-8 py-6 flex flex-col gap-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <Scale className="size-4 mt-1 mr-2 shrink-0 text-background/60" aria-hidden />
                )}
                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
                    ${msg.role === "user"
                      ? "bg-background text-foreground rounded-br-sm"
                      : "bg-background/10 text-background rounded-bl-sm"
                    }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start items-center gap-2 text-background/60 text-sm">
                <Scale className="size-4 shrink-0 animate-pulse" aria-hidden />
                <span>Thinking...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </section>
        )}
      </div>

      {/* ── Input bar – only shown pinned to bottom in chat mode ── */}
      {isChat && (
        <div className="sticky bottom-0 w-full bg-foreground border-t border-border/20 py-3 px-4 sm:px-8">
          <div className="mx-auto w-full max-w-[min(680px,100%)]">
            <ChatInput onSend={handleSend} isLoading={thinking} />
          </div>
        </div>
      )}
    </main>
  )
}

