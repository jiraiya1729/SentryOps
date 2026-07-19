import { Skeleton } from "@/components/ui/skeleton"

export default function TraceDetailLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-7 w-20" />
      <div>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="mt-1 h-4 w-72" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-9" />
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 h-9 border-t border-border">
            <Skeleton className="h-3.5 w-48" style={{ marginLeft: `${(i % 4) * 16}px` }} />
            <div className="flex-1" />
            <Skeleton className="h-4 w-32 rounded-sm" />
          </div>
        ))}
      </div>
    </div>
  )
}
