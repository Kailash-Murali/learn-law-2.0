import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/+$/, "") ?? "http://127.0.0.1:8000"

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const upstream = await fetch(`${BACKEND_URL}/api/xai/confidence-breakdown`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    if (!upstream.ok) {
      const err = await upstream.json().catch(() => ({ detail: upstream.statusText }))
      return NextResponse.json({ error: err.detail ?? "Upstream error" }, { status: upstream.status })
    }
    return NextResponse.json(await upstream.json())
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error"
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
