import { Skeleton } from "@/components/ui/skeleton"

export default function PodDetailLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-32" />

      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-5 w-16 rounded-md" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[72px] rounded-lg" />
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-4 w-28" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-[120px] rounded-lg" />
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-4 w-20" />
        <div className="rounded-lg border border-border overflow-hidden">
          <div className="bg-muted/50 h-9" />
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-3 border-t border-border">
              <Skeleton className="h-3.5 w-3.5" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-4 w-8" />
              <Skeleton className="h-4 w-28" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
