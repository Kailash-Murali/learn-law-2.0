import Link from "next/link"
import { Instagram, Linkedin, Twitter } from "lucide-react"

export function SocialLinks() {
  return (
    <nav aria-label="Social media" className="pt-2">
      <ul className="flex items-center gap-4">
        <li>
          <Link
            href="#"
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
            aria-label="Follow on Instagram"
          >
            <Instagram className="size-4" aria-hidden />
            <span className="text-sm">Instagram</span>
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
            aria-label="Connect on LinkedIn"
          >
            <Linkedin className="size-4" aria-hidden />
            <span className="text-sm">LinkedIn</span>
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
            aria-label="Follow on X"
          >
            <Twitter className="size-4" aria-hidden />
            <span className="text-sm">X</span>
          </Link>
        </li>
      </ul>
    </nav>
  )
}
