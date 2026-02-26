import CornerIcons from "@/components/learn-law/corner-icons"
import { Hero } from "@/components/learn-law/hero"
import { SearchBar } from "@/components/learn-law/search-bar"
import { LearnLawFooter } from "@/components/learn-law/footer"

export default function LearnLawPage() {
  return (
    <main className="min-h-screen bg-foreground text-background">
      {/* Corner Icons */}
      <CornerIcons />

      {/* Centered content */}
      <section className="mx-auto flex max-w-3xl flex-col items-center px-6 pb-24 pt-20 md:pt-28">
        <Hero />

        {/* Search Bar with embedded buttons, no separate Search button */}
        <div className="mt-8 w-full">
          <SearchBar />
        </div>
      </section>

      {/* Footer with social + support only (removed from main body) */}
      <LearnLawFooter />
    </main>
  )
}
