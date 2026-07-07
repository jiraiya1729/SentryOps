import { Suspense } from "react"
import { EventsTimeline } from "@/components/events/events-timeline"
import { Skeleton } from "@/components/ui/skeleton"

function EventsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 rounded-lg" />
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 w-36" />
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-8 w-32" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-md" />
        ))}
      </div>
    </div>
  )
}

export default function EventsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Events</h1>
        <p className="text-sm text-muted-foreground">
          Kubernetes cluster events and warnings
        </p>
      </div>
      <Suspense fallback={<EventsSkeleton />}>
        <EventsTimeline />
      </Suspense>
    </div>
  )
}
