/**
 * Next.js API route – proxies legal-research requests to the Python FastAPI backend.
 *
 * POST /api/research  { query: string }
 *
 * The FastAPI backend is expected at BACKEND_URL (default http://127.0.0.1:8000).
 */

import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/+$/, "") ?? "http://127.0.0.1:8000"

// ── POST handler ──────────────────────────────────────────────
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()

    if (!body.query || typeof body.query !== "string" || body.query.trim().length < 3) {
      return NextResponse.json(
        { error: "Query must be at least 3 characters." },
        { status: 400 },
      )
    }

    const upstream = await fetch(`${BACKEND_URL}/api/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: body.query.trim(),
      }),
    })

    if (!upstream.ok) {
      const err = await upstream.json().catch(() => ({ detail: upstream.statusText }))
      return NextResponse.json(
        { error: err.detail ?? "Upstream error" },
        { status: upstream.status },
      )
    }

    const data = await upstream.json()
    return NextResponse.json(data)
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error"
    console.error("[api/research] proxy error:", message)
    return NextResponse.json({ error: message }, { status: 502 })
  }
}

// ── GET handler (health pass-through) ─────────────────────────
export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/api/health`)
    const data = await upstream.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: "Backend unreachable" },
      { status: 502 },
    )
  }
}
