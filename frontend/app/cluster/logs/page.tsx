import { Suspense } from "react"
import { LogViewer } from "@/components/logs/log-viewer"
import { Skeleton } from "@/components/ui/skeleton"

function LogViewerSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-7 w-48" />
      </div>
      <Skeleton className="h-20 w-full rounded-lg" />
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-8" />
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2 border-t border-border">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-4 w-12 rounded-md" />
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 flex-1" />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Logs</h1>
        <p className="text-sm text-muted-foreground">
          Search and explore cluster logs
        </p>
      </div>
      <Suspense fallback={<LogViewerSkeleton />}>
        <LogViewer />
      </Suspense>
    </div>
  )
}
