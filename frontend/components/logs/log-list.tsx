"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import type { LogEntry } from "@/lib/types/api"
import { LogLevelBadge } from "./log-level-badge"
import { EmptyState } from "@/components/shared/empty-state"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ChevronRight, ArrowDown } from "lucide-react"

interface LogListProps {
  logs: LogEntry[]
  total: number
  isLoading: boolean
  liveMode?: boolean
}

export function LogList({ logs, total, isLoading, liveMode }: LogListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false)
  const isAtBottomRef = useRef(true)

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    isAtBottomRef.current = atBottom
    setIsUserScrolledUp(!atBottom && !!liveMode)
  }, [liveMode])

  useEffect(() => {
    if (!liveMode || !isAtBottomRef.current) return
    const el = scrollContainerRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [logs.length, liveMode])

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

  const levelBorderColor: Record<string, string> = {
    FATAL: "border-l-red-500",
    ERROR: "border-l-red-400",
    WARN: "border-l-yellow-400",
    INFO: "border-l-blue-400",
    DEBUG: "border-l-zinc-500",
    TRACE: "border-l-zinc-600",
    UNKNOWN: "border-l-zinc-600",
  }

  const levelTextColor: Record<string, string> = {
    FATAL: "text-red-400",
    ERROR: "text-red-400",
    WARN: "text-yellow-400",
    INFO: "text-blue-400",
    DEBUG: "text-zinc-500",
    TRACE: "text-zinc-600",
    UNKNOWN: "text-zinc-600",
  }

  return (
    <div className={cn(
      "rounded-lg border border-border overflow-hidden relative",
      liveMode && "border-green-500/20"
    )}>
      <div className={cn(
        "h-9 px-4 flex items-center justify-between",
        liveMode ? "bg-zinc-900/80 border-b border-green-500/10" : "bg-muted/50"
      )}>
        <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-2">
          {liveMode && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
          )}
          {liveMode
            ? `${total.toLocaleString()} lines captured`
            : `${total.toLocaleString()} log${total !== 1 ? "s" : ""} found`}
        </span>
        {liveMode && (
          <span className="text-[10px] text-green-500/70 font-mono">LIVE TAIL</span>
        )}
      </div>
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className={cn(
          "max-h-[calc(100vh-360px)] overflow-y-auto",
          liveMode ? "bg-zinc-950/50" : "divide-y divide-border"
        )}
      >
        {logs.map((log, index) => {
          const isExpanded = expandedIndex === index
          return (
            <div key={index}>
              <div
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors font-mono text-xs",
                  liveMode
                    ? cn(
                        "border-l-2 hover:bg-zinc-800/50",
                        levelBorderColor[log.log_level] || "border-l-zinc-600"
                      )
                    : cn(
                        "hover:bg-muted/30",
                        isExpanded && "bg-muted/20"
                      )
                )}
                onClick={() => setExpandedIndex(isExpanded ? null : index)}
              >
                <ChevronRight
                  className={cn(
                    "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
                    isExpanded && "rotate-90"
                  )}
                />
                <span className={cn(
                  "shrink-0 w-20 text-[11px]",
                  liveMode ? "text-zinc-500" : "text-muted-foreground"
                )}>
                  {formatTimestamp(log.timestamp)}
                </span>
                {liveMode ? (
                  <span className={cn(
                    "shrink-0 w-12 text-[10px] font-bold uppercase",
                    levelTextColor[log.log_level] || "text-zinc-500"
                  )}>
                    {log.log_level}
                  </span>
                ) : (
                  <LogLevelBadge level={log.log_level} />
                )}
                <span className={cn(
                  "shrink-0 max-w-36 truncate text-[11px]",
                  liveMode ? "text-cyan-400/70" : "text-muted-foreground"
                )}>
                  {log.pod_name}
                </span>
                <span className={cn(
                  "truncate",
                  liveMode ? "text-zinc-300" : "text-foreground"
                )}>
                  {log.message}
                </span>
              </div>
              {isExpanded && (
                <div className={cn(
                  "px-3 py-3 border-t border-border/50",
                  liveMode ? "bg-zinc-900/60" : "bg-muted/10"
                )}>
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
                          <dd className="text-foreground font-mono">{log.node_name || "—"}</dd>
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
      {liveMode && isUserScrolledUp && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
          <Button
            variant="secondary"
            size="xs"
            className="shadow-lg text-[11px] gap-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-600"
            onClick={() => {
              const el = scrollContainerRef.current
              if (el) {
                el.scrollTo({ top: el.scrollHeight, behavior: "smooth" })
                setIsUserScrolledUp(false)
                isAtBottomRef.current = true
              }
            }}
          >
            <ArrowDown className="h-3 w-3" />
            Jump to latest
          </Button>
        </div>
      )}
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
