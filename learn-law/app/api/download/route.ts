/**
 * Next.js API route – proxies file-download requests to the Python FastAPI backend.
 *
 * GET /api/download?path=<server-side-path>
 */

import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/+$/, "") ?? "http://127.0.0.1:8000"

export async function GET(req: NextRequest) {
  const filePath = req.nextUrl.searchParams.get("path")
  if (!filePath) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 })
  }

  try {
    const upstream = await fetch(
      `${BACKEND_URL}/api/download?path=${encodeURIComponent(filePath)}`,
    )

    if (!upstream.ok) {
      const err = await upstream.json().catch(() => ({ detail: upstream.statusText }))
      return NextResponse.json(
        { error: err.detail ?? "Upstream error" },
        { status: upstream.status },
      )
    }

    const blob = await upstream.blob()
    const filename =
      upstream.headers.get("content-disposition")?.match(/filename="?(.+?)"?$/)?.[1] ??
      filePath.split("/").pop() ??
      "download"

    return new NextResponse(blob, {
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Download failed"
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
