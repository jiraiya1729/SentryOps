import { Suspense } from "react"
import { MetricsDashboard } from "@/components/metrics/metrics-dashboard"
import { Skeleton } from "@/components/ui/skeleton"

function MetricsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-8 w-36" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Skeleton className="h-80 rounded-lg" />
        <Skeleton className="h-80 rounded-lg" />
      </div>
    </div>
  )
}

export default function MetricsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Metrics</h1>
        <p className="text-sm text-muted-foreground">
          CPU and memory usage across your cluster
        </p>
      </div>
      <Suspense fallback={<MetricsSkeleton />}>
        <MetricsDashboard />
      </Suspense>
    </div>
  )
}
