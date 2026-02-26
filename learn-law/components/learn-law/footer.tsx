import Link from "next/link"
import { SocialLinks } from "@/components/learn-law/social-links"

export function Footer() {
  return (
    <footer className="mt-10 border-t border-border">
      <div className="w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <SocialLinks />
          <nav aria-label="Support links">
            <ul className="flex items-center gap-4">
              <li>
                <Link
                  href="#"
                  className="inline-flex items-center rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  Contact
                </Link>
              </li>
              <li>
                <Link
                  href="#"
                  className="inline-flex items-center rounded-md border border-border px-3 py-2 hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  Support
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </footer>
  )
}

export { Footer as LearnLawFooter }
