import Link from "next/link"
import { Scale, ArrowLeft } from "lucide-react"

export default function SettingsPage() {
  return (
    <main className="min-h-dvh bg-foreground text-background flex flex-col">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-10 flex w-full items-center justify-between px-4 py-2 border-b border-border/20 bg-foreground">
        <Link
          href="/"
          aria-label="Back to home"
          className="flex items-center gap-1.5 text-sm text-background/60 hover:text-background transition-colors"
        >
          <ArrowLeft className="size-4" aria-hidden />
          <span>Back</span>
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-background/70">Learn Law</span>
          <Scale className="size-5 text-background" aria-hidden />
        </div>
      </div>

      {/* ── Body ── */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 text-center gap-2">
        <h1 className="text-2xl font-semibold text-background">Settings</h1>
        <p className="text-sm text-background/50">Configuration options coming soon.</p>
      </section>
    </main>
  )
}
