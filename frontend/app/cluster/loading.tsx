import { Skeleton } from "@/components/ui/skeleton"

export default function ClusterLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-64" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[88px] rounded-lg" />
        ))}
      </div>

      <div className="space-y-4">
        <Skeleton className="h-9 w-48" />
        <div className="space-y-3">
          <div className="flex gap-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-8 w-20" />
          </div>
          <div className="rounded-lg border border-border overflow-hidden">
            <div className="bg-muted/50 h-9" />
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 p-3 border-t border-border">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-16 rounded-md" />
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-4 w-8" />
                <Skeleton className="h-4 w-32" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
