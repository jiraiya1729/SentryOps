"use client"

import { useState, useEffect } from "react"
import { getTraceCorrelation, getResourceCorrelation } from "@/lib/api/traces"
import type { TraceCorrelationResult, ResourceCorrelationResult } from "@/lib/types/api"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, Activity, FileText, Zap, GitBranch } from "lucide-react"

type CorrelationResult = TraceCorrelationResult | ResourceCorrelationResult

interface Props {
  traceId?: string
  namespace?: string
  podName?: string
  sinceMinutes?: number
}

type TabKey = "spans" | "logs" | "events" | "metrics"

function TabButton({
  label,
  count,
  active,
  onClick,
}: {
  label: string
  count: number
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
        active
          ? "bg-accent text-accent-foreground font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-muted"
      }`}
    >
      {label}
      {count > 0 && (
        <Badge variant="secondary" className="text-xs px-1.5 py-0 h-4">
          {count}
        </Badge>
      )}
    </button>
  )
}

export function CorrelationPanel({ traceId, namespace, podName, sinceMinutes = 15 }: Props) {
  const [data, setData] = useState<CorrelationResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>("logs")

  useEffect(() => {
    setLoading(true)
    setError(null)

    const fetch = traceId
      ? getTraceCorrelation(traceId)
      : namespace && podName
        ? getResourceCorrelation(namespace, podName, sinceMinutes)
        : Promise.reject(new Error("Provide traceId or namespace+podName"))

    fetch
      .then((result) => setData(result))
      .catch((e) => setError(e.message ?? "Failed to load correlated signals"))
      .finally(() => setLoading(false))
  }, [traceId, namespace, podName, sinceMinutes])

  if (loading) {
    return (
      <div className="space-y-2 p-4">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground p-4">
        <AlertCircle className="h-4 w-4" />
        <span>{error}</span>
      </div>
    )
  }

  if (!data) return null

  const spans = "spans" in data ? data.spans : []
  const logs = data.logs ?? []
  const events = data.events ?? []
  const metrics = data.metrics ?? []

  const timeRange = data.time_range
    ? `${new Date(data.time_range.start).toLocaleTimeString()} – ${new Date(data.time_range.end).toLocaleTimeString()}`
    : null

  const tabs: { key: TabKey; label: string; count: number; icon: React.ReactNode }[] = [
    { key: "spans", label: "Spans", count: spans.length, icon: <GitBranch className="h-3.5 w-3.5" /> },
    { key: "logs", label: "Logs", count: logs.length, icon: <FileText className="h-3.5 w-3.5" /> },
    { key: "events", label: "Events", count: events.length, icon: <Zap className="h-3.5 w-3.5" /> },
    { key: "metrics", label: "Metrics", count: metrics.length, icon: <Activity className="h-3.5 w-3.5" /> },
  ]

  return (
    <div className="border rounded-lg bg-card">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">Related Signals</span>
          {timeRange && <span className="text-xs text-muted-foreground font-mono">{timeRange}</span>}
        </div>
      </div>

      <div className="flex gap-1 px-3 pt-3">
        {tabs.map((tab) => (
          <TabButton
            key={tab.key}
            label={tab.label}
            count={tab.count}
            active={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
          />
        ))}
      </div>

      <div className="p-4 max-h-72 overflow-y-auto">
        {activeTab === "spans" && (
          <div className="space-y-1">
            {spans.length === 0 ? (
              <p className="text-xs text-muted-foreground">No spans found.</p>
            ) : (
              spans.slice(0, 50).map((span) => (
                <div key={span.span_id} className="flex items-center gap-2 text-xs font-mono py-1 border-b border-border/40 last:border-0">
                  <Badge variant={span.status_code === "ERROR" ? "destructive" : "secondary"} className="text-[10px] px-1 py-0">
                    {span.service_name}
                  </Badge>
                  <span className="text-muted-foreground truncate flex-1">{span.operation_name}</span>
                  <span className="text-muted-foreground">{span.duration_ms.toFixed(1)}ms</span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "logs" && (
          <div className="space-y-1">
            {logs.length === 0 ? (
              <p className="text-xs text-muted-foreground">No related logs found.</p>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="text-xs py-1.5 border-b border-border/40 last:border-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-mono text-muted-foreground">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <Badge
                      variant={log.level === "ERROR" || log.level === "FATAL" ? "destructive" : log.level === "WARN" ? "outline" : "secondary"}
                      className="text-[10px] px-1 py-0"
                    >
                      {log.level}
                    </Badge>
                    <span className="text-muted-foreground">{log.pod}</span>
                  </div>
                  <p className="font-mono text-xs text-foreground/80 truncate">{log.message}</p>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "events" && (
          <div className="space-y-1">
            {events.length === 0 ? (
              <p className="text-xs text-muted-foreground">No related events found.</p>
            ) : (
              events.map((evt, i) => (
                <div key={i} className="text-xs py-1.5 border-b border-border/40 last:border-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-mono text-muted-foreground">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                    <Badge
                      variant={evt.type === "Warning" ? "outline" : "secondary"}
                      className="text-[10px] px-1 py-0"
                    >
                      {evt.reason}
                    </Badge>
                    <span className="text-muted-foreground">{evt.object}</span>
                  </div>
                  <p className="font-mono text-xs text-foreground/80 truncate">{evt.message}</p>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "metrics" && (
          <div className="space-y-1">
            {metrics.length === 0 ? (
              <p className="text-xs text-muted-foreground">No related metrics found.</p>
            ) : (
              metrics.map((m, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-border/40 last:border-0 font-mono">
                  <span className="text-muted-foreground">{new Date(m.timestamp).toLocaleTimeString()}</span>
                  <span className="flex-1 truncate">{m.metric_name}</span>
                  <span className="font-medium">{typeof m.value === "number" ? m.value.toFixed(4) : m.value}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
