import { Skeleton } from "@/components/ui/skeleton"

export default function TracesLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="mt-1 h-4 w-56" />
      </div>
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-40" />
        </div>
        <div className="rounded-lg border border-border overflow-hidden">
          <div className="bg-muted/50 h-9" />
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-t border-border">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
