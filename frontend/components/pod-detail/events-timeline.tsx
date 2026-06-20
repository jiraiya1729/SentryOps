import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { AlertTriangle, Info } from "lucide-react"
import type { PodEvent } from "@/lib/types/api"
import { cn } from "@/lib/utils"
import { EmptyState } from "@/components/shared/empty-state"

interface EventsTimelineProps {
  events: PodEvent[]
}

export function EventsTimeline({ events }: EventsTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Events</h2>
        <EmptyState title="No events" message="No events recorded for this pod." />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">
        Events ({events.length})
      </h2>
      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="h-9 text-xs font-medium text-muted-foreground bg-muted/50 w-8" />
              <TableHead className="h-9 text-xs font-medium text-muted-foreground bg-muted/50">
                Reason
              </TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground bg-muted/50">
                Message
              </TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground bg-muted/50 w-16">
                Count
              </TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground bg-muted/50 w-40">
                Last Seen
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((event, i) => {
              const isWarning = event.type === "Warning"
              return (
                <TableRow
                  key={`${event.reason}-${i}`}
                  className={cn(
                    "border-border transition-colors",
                    isWarning
                      ? "bg-destructive/5 hover:bg-destructive/10"
                      : "hover:bg-muted/30"
                  )}
                >
                  <TableCell className="py-2.5">
                    {isWarning ? (
                      <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                    ) : (
                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </TableCell>
                  <TableCell className="py-2.5">
                    <span
                      className={cn(
                        "text-sm font-medium",
                        isWarning && "text-destructive"
                      )}
                    >
                      {event.reason}
                    </span>
                  </TableCell>
                  <TableCell className="py-2.5 text-sm text-muted-foreground max-w-[400px] truncate">
                    {event.message}
                  </TableCell>
                  <TableCell className="py-2.5 text-sm text-muted-foreground">
                    {event.count}
                  </TableCell>
                  <TableCell className="py-2.5 text-xs text-muted-foreground font-mono">
                    {formatTimestamp(event.timestamp)}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts)
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  } catch {
    return ts
  }
}
