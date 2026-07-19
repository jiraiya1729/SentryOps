import { Skeleton } from "@/components/ui/skeleton"

export default function ServicesLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="mt-1 h-4 w-64" />
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-9" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-6 px-4 py-3 border-t border-border">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </div>
  )
}
