"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { getEvents, getEventStats } from "@/lib/api/events"
import { getNamespaces } from "@/lib/api/namespaces"
import type { K8sEvent, EventStatsResponse, Namespace } from "@/lib/types/api"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { Network, RefreshCw, AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"

const TIME_RANGES = ["1h", "6h", "24h", "7d"] as const

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

function StatsBar({ stats }: { stats: EventStatsResponse }) {
  const warning = stats.summary["Warning"]
  const normal = stats.summary["Normal"]
  const warningCount = warning?.total ?? 0
  const normalCount = normal?.total ?? 0
  const affectedResources = Math.max(
    warning?.affected_resources ?? 0,
    normal?.affected_resources ?? 0
  )

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-2.5 text-sm">
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-orange-500" />
        <span className="font-medium">{warningCount.toLocaleString()}</span>
        <span className="text-muted-foreground">Warning</span>
      </div>
      <div className="text-border">|</div>
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-zinc-500" />
        <span className="font-medium">{normalCount.toLocaleString()}</span>
        <span className="text-muted-foreground">Normal</span>
      </div>
      {affectedResources > 0 && (
        <>
          <div className="text-border">|</div>
          <span className="text-muted-foreground">
            <span className="font-medium text-foreground">{affectedResources}</span> resources affected
          </span>
        </>
      )}
    </div>
  )
}

function EventRow({ event }: { event: K8sEvent }) {
  const [expanded, setExpanded] = useState(false)
  const isWarning = event.type === "Warning"

  const resourceLink =
    event.involved_object_kind === "Pod"
      ? `/cluster/pods/${event.namespace}/${event.involved_object_name}`
      : null

  return (
    <div
      className={cn(
        "border-l-2 rounded-r-md px-4 py-3 cursor-pointer transition-colors",
        isWarning
          ? "border-l-orange-500 bg-orange-500/5 hover:bg-orange-500/10"
          : "border-l-zinc-700 hover:bg-muted/30"
      )}
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "mt-1 shrink-0 h-2 w-2 rounded-full",
            isWarning ? "bg-orange-500" : "bg-zinc-500"
          )}
        />

        <div className="min-w-0 flex-1 space-y-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-muted-foreground shrink-0">
              {formatRelativeTime(event.timestamp)}
            </span>

            <span
              className={cn(
                "text-xs font-semibold",
                isWarning ? "text-orange-400" : "text-muted-foreground"
              )}
            >
              {event.reason}
            </span>

            {resourceLink ? (
              <Link
                href={resourceLink}
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
              >
                {event.involved_object_kind}/{event.involved_object_name}
              </Link>
            ) : (
              <span className="inline-flex items-center rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                {event.involved_object_kind}/{event.involved_object_name}
              </span>
            )}

            <span className="text-[10px] text-muted-foreground">{event.namespace}</span>

            {event.count > 1 && (
              <span
                className={cn(
                  "ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                  isWarning
                    ? "bg-orange-500/20 text-orange-400"
                    : "bg-zinc-700 text-zinc-400"
                )}
              >
                ×{event.count}
              </span>
            )}
          </div>

          <p className={cn("text-xs", expanded ? "" : "truncate", "text-muted-foreground")}>
            {event.message}
          </p>

          {expanded && (
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs border-t border-border/50 pt-2">
              <dt className="text-muted-foreground">Source</dt>
              <dd className="font-mono text-foreground">{event.source_component}</dd>
              <dt className="text-muted-foreground">First seen</dt>
              <dd className="font-mono text-foreground">{new Date(event.first_timestamp).toLocaleString()}</dd>
              <dt className="text-muted-foreground">Last seen</dt>
              <dd className="font-mono text-foreground">{new Date(event.last_timestamp).toLocaleString()}</dd>
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}

export function EventsTimeline() {
  const [timeRange, setTimeRange] = useState<string>("1h")
  const [namespace, setNamespace] = useState("")
  const [namespaces, setNamespaces] = useState<Namespace[]>([])
  const [warningOnly, setWarningOnly] = useState(false)
  const [events, setEvents] = useState<K8sEvent[]>([])
  const [stats, setStats] = useState<EventStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [eventsRes, statsRes] = await Promise.all([
        getEvents({
          namespace: namespace || undefined,
          event_type: warningOnly ? "Warning" : undefined,
          since: timeRange,
          limit: 200,
        }),
        getEventStats(namespace || undefined, timeRange),
      ])
      setEvents(eventsRes.events)
      setStats(statsRes)
      setLastUpdated(new Date())
    } catch {
      // Keep previous data on error
    } finally {
      setLoading(false)
    }
  }, [timeRange, namespace, warningOnly])

  useEffect(() => {
    getNamespaces().then((res) => setNamespaces(res.items)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchData()
    intervalRef.current = setInterval(fetchData, 10000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchData])

  const timeSince = lastUpdated
    ? Math.round((Date.now() - lastUpdated.getTime()) / 1000)
    : null

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      {!loading && stats && <StatsBar stats={stats} />}
      {loading && <Skeleton className="h-10 rounded-lg" />}

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 h-8 text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors">
            <Network className="h-3.5 w-3.5" />
            {namespace || "All Namespaces"}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => setNamespace("")}>All Namespaces</DropdownMenuItem>
            {namespaces.map((ns) => (
              <DropdownMenuItem key={ns.name} onClick={() => setNamespace(ns.name)}>
                {ns.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
          {TIME_RANGES.map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? "default" : "ghost"}
              size="xs"
              onClick={() => setTimeRange(range)}
            >
              {range}
            </Button>
          ))}
        </div>

        <Button
          variant={warningOnly ? "default" : "outline"}
          size="xs"
          onClick={() => setWarningOnly((v) => !v)}
          className={cn(
            "gap-1.5",
            warningOnly && "bg-orange-500 hover:bg-orange-600 border-orange-500 text-white"
          )}
        >
          <AlertTriangle className="h-3 w-3" />
          Warnings only
        </Button>

        {timeSince !== null && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground ml-auto">
            <RefreshCw className="h-3 w-3" />
            <span>Updated {timeSince}s ago</span>
          </div>
        )}
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="border-l-2 border-l-zinc-700 px-4 py-3 space-y-1.5">
              <div className="flex items-center gap-2">
                <Skeleton className="h-3 w-14" />
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-5 w-32 rounded" />
              </div>
              <Skeleton className="h-3 w-3/4" />
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-lg border border-border">
          <EmptyState
            title="No events found"
            message="Try adjusting your filters or time range."
          />
        </div>
      ) : (
        <div className="space-y-1.5">
          {events.map((event, i) => (
            <EventRow key={`${event.name}-${event.timestamp}-${i}`} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}
