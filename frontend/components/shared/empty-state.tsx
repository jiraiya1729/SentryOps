import { Inbox } from "lucide-react"

interface EmptyStateProps {
  title?: string
  message?: string
}

export function EmptyState({
  title = "No data",
  message = "There's nothing to display yet.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-muted">
        <Inbox className="h-6 w-6 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-medium">{title}</h3>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}
