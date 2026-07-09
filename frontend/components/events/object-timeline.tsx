"use client"

import { useState, useEffect } from "react"
import { GitBranch, AlertTriangle } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { getObjectTimeline } from "@/lib/api/events"
import { PatternAlerts } from "./pattern-alerts"
import type { ObjectTimelineResponse } from "@/lib/types/api"

export interface SelectedResource {
  namespace: string
  kind: string
  name: string
}

interface ObjectTimelineProps {
  resource: SelectedResource | null
  onClose: () => void
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return "just now"
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function ObjectTimeline({ resource, onClose }: ObjectTimelineProps) {
  const [data, setData] = useState<ObjectTimelineResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!resource) return
    setLoading(true)
    setData(null)
    getObjectTimeline(resource.namespace, resource.kind, resource.name)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [resource])

  return (
    <Sheet open={resource !== null} onOpenChange={(v) => { if (!v) onClose() }}>
      <SheetContent
        side="right"
        className="flex w-[480px] flex-col gap-0 p-0 sm:max-w-[480px] bg-card"
        showCloseButton={true}
      >
        <SheetHeader className="border-b border-border px-4 pb-3 pt-4">
          <SheetTitle className="flex items-center gap-2 text-sm">
            <GitBranch className="h-4 w-4 text-muted-foreground" />
            {resource ? (
              <>
                <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                  {resource.kind}
                </span>
                <span className="font-mono text-foreground">{resource.name}</span>
              </>
            ) : (
              "Object Timeline"
            )}
          </SheetTitle>
          {resource && (
            <SheetDescription className="text-xs text-muted-foreground mt-0.5">
              {resource.namespace}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-md" />
              ))}
            </div>
          ) : (
            <>
              {data?.patterns && data.patterns.length > 0 && (
                <PatternAlerts patterns={data.patterns} />
              )}

              {data?.events && data.events.length > 0 ? (
                <div className="space-y-1.5">
                  {data.events.map((event, i) => {
                    const isWarning = event.type === "Warning"
                    return (
                      <div
                        key={`${event.name}-${event.timestamp}-${i}`}
                        className={cn(
                          "border-l-2 rounded-r-md px-3 py-2.5",
                          isWarning
                            ? "border-l-orange-500 bg-orange-500/5"
                            : "border-l-zinc-700 bg-muted/20"
                        )}
                      >
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[10px] text-muted-foreground">
                            {formatRelativeTime(event.timestamp)}
                          </span>
                          {isWarning && (
                            <AlertTriangle className="h-3 w-3 text-orange-500 shrink-0" />
                          )}
                          <span
                            className={cn(
                              "text-xs font-semibold",
                              isWarning ? "text-orange-400" : "text-muted-foreground"
                            )}
                          >
                            {event.reason}
                          </span>
                          {event.count > 1 && (
                            <span className="ml-auto text-[10px] text-muted-foreground">
                              ×{event.count}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {event.message}
                        </p>
                      </div>
                    )
                  })}
                </div>
              ) : !loading && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No events found for this object.
                </p>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
