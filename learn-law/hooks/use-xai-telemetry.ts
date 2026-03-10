"use client"

import { useRef, useEffect, useCallback } from "react"

/**
 * Tracks how long a user views an XAI panel and sends telemetry
 * asynchronously via navigator.sendBeacon (non-blocking).
 *
 * Usage:
 *   const { onOpen, onClose } = useXaiTelemetry("shap_waterfall")
 *   // call onOpen() when panel expands, onClose() when it collapses
 */
export function useXaiTelemetry(featureName: string) {
  const entryTimeRef = useRef<number | null>(null)
  const batchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingRef = useRef<Array<Record<string, unknown>>>([])

  const flush = useCallback(() => {
    if (pendingRef.current.length === 0) return
    const payload = JSON.stringify(pendingRef.current)
    pendingRef.current = []
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      const blob = new Blob([payload], { type: "application/json" })
      navigator.sendBeacon("/api/feedback", blob)
    } else {
      // fallback: non-blocking fetch
      const schedule = typeof requestIdleCallback !== "undefined" ? requestIdleCallback : (cb: () => void) => setTimeout(cb, 0)
      schedule(() => {
        fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: true,
        }).catch(() => {})
      })
    }
  }, [])

  const enqueue = useCallback(
    (timeMs: number) => {
      pendingRef.current.push({
        message_id: `xai-${featureName}-${Date.now()}`,
        vote: "up",
        xai_feature_used: featureName,
        time_spent_viewing_ms: timeMs,
      })
      // Batch within 2 seconds
      if (batchTimerRef.current) clearTimeout(batchTimerRef.current)
      batchTimerRef.current = setTimeout(flush, 2000)
    },
    [featureName, flush],
  )

  const onOpen = useCallback(() => {
    entryTimeRef.current = Date.now()
  }, [])

  const onClose = useCallback(() => {
    if (entryTimeRef.current === null) return
    const elapsed = Date.now() - entryTimeRef.current
    entryTimeRef.current = null
    enqueue(elapsed)
  }, [enqueue])

  // Flush on unmount
  useEffect(() => {
    return () => {
      if (entryTimeRef.current !== null) {
        const elapsed = Date.now() - entryTimeRef.current
        entryTimeRef.current = null
        enqueue(elapsed)
      }
      flush()
    }
  }, [enqueue, flush])

  return { onOpen, onClose }
}
