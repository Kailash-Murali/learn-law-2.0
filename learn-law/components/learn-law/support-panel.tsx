import Link from "next/link"
import { Card } from "@/components/ui/card"
import { ArrowRight } from "lucide-react"

export function SupportPanel() {
  return (
    <Card className="p-6 bg-card">
      <div className="space-y-4">
        <h3 className="text-xl font-semibold">Support</h3>
        <ul className="space-y-2">
          <li>
            <Link
              href="#"
              className="group inline-flex items-center justify-between w-full rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <span>Contact</span>
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </li>
          <li>
            <Link
              href="#"
              className="group inline-flex items-center justify-between w-full rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <span>Support</span>
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </li>
        </ul>
      </div>
    </Card>
  )
}
