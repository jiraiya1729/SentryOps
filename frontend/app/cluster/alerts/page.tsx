import { Suspense } from "react"
import { SuggestionsSection } from "@/components/alerts/suggestions-section"

export default function AlertsPage() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Alerts</h1>
      <Suspense
        fallback={
          <div className="text-muted-foreground text-sm">Loading suggestions…</div>
        }
      >
        <SuggestionsSection />
      </Suspense>
    </div>
  )
}
