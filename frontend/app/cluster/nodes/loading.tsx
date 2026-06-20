import { Skeleton } from "@/components/ui/skeleton"

export default function NodesLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-9" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-3 border-t border-border">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-5 w-16 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  )
}
