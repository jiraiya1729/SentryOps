"use client"

import { useState } from "react"
import type { LogEntry } from "@/lib/types/api"
import { LogLevelBadge } from "./log-level-badge"
import { EmptyState } from "@/components/shared/empty-state"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { ChevronRight } from "lucide-react"

interface LogListProps {
  logs: LogEntry[]
  total: number
  isLoading: boolean
}

export function LogList({ logs, total, isLoading }: LogListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-8 px-3 flex items-center">
          <Skeleton className="h-3 w-24" />
        </div>
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2 border-t border-border">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-4 w-12 rounded-md" />
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 flex-1" />
          </div>
        ))}
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <div className="rounded-lg border border-border overflow-hidden">
        <EmptyState
          title="No logs found"
          message="Try adjusting your filters or time range."
        />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="bg-muted/50 h-8 px-3 flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground font-medium">
          {total.toLocaleString()} log{total !== 1 ? "s" : ""} found
        </span>
      </div>
      <div className="divide-y divide-border max-h-[calc(100vh-360px)] overflow-y-auto">
        {logs.map((log, index) => {
          const isExpanded = expandedIndex === index
          return (
            <div key={index}>
              <div
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-muted/30 transition-colors font-mono text-xs",
                  isExpanded && "bg-muted/20"
                )}
                onClick={() => setExpandedIndex(isExpanded ? null : index)}
              >
                <ChevronRight
                  className={cn(
                    "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
                    isExpanded && "rotate-90"
                  )}
                />
                <span className="text-muted-foreground shrink-0 w-20 text-[11px]">
                  {formatTimestamp(log.timestamp)}
                </span>
                <LogLevelBadge level={log.log_level} />
                <span className="text-muted-foreground shrink-0 max-w-32 truncate text-[11px]">
                  {log.pod_name}
                </span>
                <span className="truncate text-foreground">{log.message}</span>
              </div>
              {isExpanded && (
                <div className="px-3 py-3 bg-muted/10 border-t border-border/50">
                  <div className="ml-5 space-y-3">
                    <div>
                      <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wide">
                        Message
                      </span>
                      <pre className="mt-1 text-xs text-foreground whitespace-pre-wrap break-all font-mono bg-background rounded-md p-2 border border-border">
                        {log.message}
                      </pre>
                    </div>
                    {log.parsed_fields && Object.keys(log.parsed_fields).length > 0 && (
                      <div>
                        <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wide">
                          Parsed Fields
                        </span>
                        <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                          {Object.entries(log.parsed_fields).map(([key, value]) => (
                            <div key={key} className="contents">
                              <dt className="text-muted-foreground font-mono">{key}</dt>
                              <dd className="text-foreground font-mono break-all">{value}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}
                    <div>
                      <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wide">
                        Metadata
                      </span>
                      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                        <div className="contents">
                          <dt className="text-muted-foreground">Namespace</dt>
                          <dd className="text-foreground font-mono">{log.namespace}</dd>
                        </div>
                        <div className="contents">
                          <dt className="text-muted-foreground">Pod</dt>
                          <dd className="text-foreground font-mono">{log.pod_name}</dd>
                        </div>
                        <div className="contents">
                          <dt className="text-muted-foreground">Container</dt>
                          <dd className="text-foreground font-mono">{log.container_name}</dd>
                        </div>
                        <div className="contents">
                          <dt className="text-muted-foreground">Node</dt>
                          <dd className="text-foreground font-mono">{log.node_name}</dd>
                        </div>
                        <div className="contents">
                          <dt className="text-muted-foreground">Stream</dt>
                          <dd className="text-foreground font-mono">{log.stream}</dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso)
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    } as Intl.DateTimeFormatOptions)
  } catch {
    return iso
  }
}
