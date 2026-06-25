"use client"

import { useMemo } from "react"
import type { LogStatEntry } from "@/lib/types/api"
import { levelBarColors } from "./log-level-badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface LogHistogramProps {
  buckets: LogStatEntry[]
  isLoading: boolean
}

interface AggregatedBucket {
  minute: string
  total: number
  levels: Record<string, number>
}

export function LogHistogram({ buckets, isLoading }: LogHistogramProps) {
  const aggregated = useMemo(() => {
    const map = new Map<string, AggregatedBucket>()
    for (const entry of buckets) {
      const existing = map.get(entry.minute)
      if (existing) {
        existing.total += entry.count
        existing.levels[entry.level] = (existing.levels[entry.level] ?? 0) + entry.count
      } else {
        map.set(entry.minute, {
          minute: entry.minute,
          total: entry.count,
          levels: { [entry.level]: entry.count },
        })
      }
    }
    return Array.from(map.values()).sort((a, b) => a.minute.localeCompare(b.minute))
  }, [buckets])

  const maxCount = useMemo(
    () => Math.max(1, ...aggregated.map((b) => b.total)),
    [aggregated]
  )

  if (isLoading) {
    return <Skeleton className="h-20 w-full rounded-lg" />
  }

  if (aggregated.length === 0) {
    return (
      <div className="flex items-center justify-center h-20 rounded-lg border border-border bg-muted/20">
        <span className="text-xs text-muted-foreground">No log volume data</span>
      </div>
    )
  }

  const levelOrder = ["FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE", "UNKNOWN"]

  return (
    <div className="rounded-lg border border-border bg-muted/10 p-3">
      <div className="flex items-end gap-px h-16 w-full">
        {aggregated.map((bucket) => (
          <div
            key={bucket.minute}
            className="flex-1 flex flex-col justify-end min-w-0 group relative"
            title={`${formatTime(bucket.minute)}: ${bucket.total} logs`}
          >
            <div
              className="w-full rounded-t-sm overflow-hidden flex flex-col-reverse"
              style={{ height: `${(bucket.total / maxCount) * 100}%` }}
            >
              {levelOrder.map((level) => {
                const count = bucket.levels[level]
                if (!count) return null
                const pct = (count / bucket.total) * 100
                return (
                  <div
                    key={level}
                    className={cn(
                      "w-full shrink-0",
                      levelBarColors[level] ?? "bg-muted-foreground/30"
                    )}
                    style={{ height: `${pct}%` }}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatTime(isoMinute: string): string {
  try {
    const date = new Date(isoMinute)
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  } catch {
    return isoMinute
  }
}
