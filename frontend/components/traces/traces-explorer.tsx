"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import {
  searchTraces,
  getServices,
  getOperations,
  type TraceSearchParams,
} from "@/lib/api/traces"
import type { TraceSummary, ServiceStats } from "@/lib/types/api"
import { getServiceColor, formatDuration, relativeTime } from "@/lib/traces-utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const TIME_RANGES = [
  { label: "15m", value: "15m" },
  { label: "1h", value: "1h" },
  { label: "6h", value: "6h" },
  { label: "24h", value: "24h" },
]

const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "OK", value: "OK" },
  { label: "Error", value: "ERROR" },
]

export function TracesExplorer() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const serviceParam = searchParams.get("service") ?? ""
  const operationParam = searchParams.get("operation") ?? ""
  const statusParam = searchParams.get("status") ?? ""
  const sinceParam = searchParams.get("since") ?? "1h"

  const [services, setServices] = useState<ServiceStats[]>([])
  const [operations, setOperations] = useState<string[]>([])
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [minDuration, setMinDuration] = useState(searchParams.get("min_duration") ?? "")
  const [maxDuration, setMaxDuration] = useState(searchParams.get("max_duration") ?? "")

  function updateURL(updates: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString())
    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value)
      else params.delete(key)
    }
    router.replace(`/cluster/traces?${params.toString()}`, { scroll: false })
  }

  // Load services list on mount
  useEffect(() => {
    getServices(sinceParam)
      .then((data) => setServices(data.services))
      .catch(() => {})
  }, [sinceParam])

  // Load operations when service changes
  useEffect(() => {
    if (!serviceParam) {
      setOperations([])
      return
    }
    getOperations(serviceParam, sinceParam)
      .then((data) => setOperations(data.operations.map((o) => o.operation_name)))
      .catch(() => setOperations([]))
  }, [serviceParam, sinceParam])

  // Fetch traces on filter change
  const fetchTraces = useCallback(() => {
    setIsLoading(true)
    const params: TraceSearchParams = {
      since: sinceParam || "1h",
      limit: 50,
    }
    if (serviceParam) params.service = serviceParam
    if (operationParam) params.operation = operationParam
    if (statusParam === "OK" || statusParam === "ERROR") params.status = statusParam
    if (minDuration) params.min_duration_ms = Number(minDuration)
    if (maxDuration) params.max_duration_ms = Number(maxDuration)

    searchTraces(params)
      .then((data) => {
        setTraces(data.traces)
        setError(null)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to fetch traces")
      })
      .finally(() => setIsLoading(false))
  }, [serviceParam, operationParam, statusParam, sinceParam, minDuration, maxDuration])

  useEffect(() => {
    fetchTraces()
  }, [fetchTraces])

  const maxDurationInPage = Math.max(...traces.map((t) => t.duration_ms), 1)

  return (
    <div className="space-y-4">
      {/* Filter toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Service */}
        <select
          value={serviceParam}
          onChange={(e) => updateURL({ service: e.target.value, operation: "" })}
          className="h-8 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All Services</option>
          {services.map((s) => (
            <option key={s.service_name} value={s.service_name}>
              {s.service_name}
            </option>
          ))}
        </select>

        {/* Operation */}
        <select
          value={operationParam}
          onChange={(e) => updateURL({ operation: e.target.value })}
          disabled={!serviceParam}
          className="h-8 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        >
          <option value="">All Operations</option>
          {operations.map((op) => (
            <option key={op} value={op}>
              {op}
            </option>
          ))}
        </select>

        {/* Status */}
        <div className="flex items-center rounded-md border border-input overflow-hidden">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => updateURL({ status: opt.value })}
              className={`h-8 px-3 text-xs transition-colors ${
                statusParam === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted/50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Time range */}
        <div className="flex items-center rounded-md border border-input overflow-hidden">
          {TIME_RANGES.map((tr) => (
            <button
              key={tr.value}
              onClick={() => updateURL({ since: tr.value })}
              className={`h-8 px-3 text-xs transition-colors ${
                sinceParam === tr.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted/50"
              }`}
            >
              {tr.label}
            </button>
          ))}
        </div>

        {/* Duration range */}
        <div className="flex items-center gap-1">
          <Input
            placeholder="Min ms"
            value={minDuration}
            onChange={(e) => setMinDuration(e.target.value)}
            onBlur={() => updateURL({ min_duration: minDuration })}
            className="h-8 w-20 text-xs"
          />
          <span className="text-xs text-muted-foreground">–</span>
          <Input
            placeholder="Max ms"
            value={maxDuration}
            onChange={(e) => setMaxDuration(e.target.value)}
            onBlur={() => updateURL({ max_duration: maxDuration })}
            className="h-8 w-20 text-xs"
          />
        </div>

        <Button variant="ghost" size="sm" onClick={fetchTraces} className="h-8 text-xs">
          Refresh
        </Button>
      </div>

      {/* Results */}
      {error ? (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[2fr_120px_200px_60px_80px_100px] items-center gap-4 px-4 h-9 bg-muted/50 border-b border-border">
            <span className="text-xs font-medium text-muted-foreground">Root Operation</span>
            <span className="text-xs font-medium text-muted-foreground">Services</span>
            <span className="text-xs font-medium text-muted-foreground">Duration</span>
            <span className="text-xs font-medium text-muted-foreground">Spans</span>
            <span className="text-xs font-medium text-muted-foreground">Status</span>
            <span className="text-xs font-medium text-muted-foreground">Time</span>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : traces.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No traces found for the selected filters.
            </div>
          ) : (
            traces.map((trace) => (
              <div
                key={trace.trace_id}
                onClick={() => router.push(`/cluster/traces/${trace.trace_id}`)}
                className="grid grid-cols-[2fr_120px_200px_60px_80px_100px] items-center gap-4 px-4 py-2.5 border-t border-border hover:bg-muted/30 cursor-pointer transition-colors"
              >
                {/* Root operation */}
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{trace.root_operation}</p>
                  <p className="text-xs text-muted-foreground font-mono truncate">{trace.trace_id}</p>
                </div>

                {/* Service dots */}
                <div className="flex items-center gap-1 flex-wrap">
                  {trace.services.slice(0, 5).map((svc) => (
                    <span
                      key={svc}
                      title={svc}
                      className="h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: getServiceColor(svc) }}
                    />
                  ))}
                  {trace.services.length > 5 && (
                    <span className="text-xs text-muted-foreground">+{trace.services.length - 5}</span>
                  )}
                </div>

                {/* Duration bar */}
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-4 rounded-sm bg-muted/50 overflow-hidden">
                    <div
                      className="h-full rounded-sm bg-gradient-to-r from-primary/60 to-primary/30"
                      style={{
                        width: `${Math.max(2, (trace.duration_ms / maxDurationInPage) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground w-14 shrink-0 text-right">
                    {formatDuration(trace.duration_ms)}
                  </span>
                </div>

                {/* Span count */}
                <span className="text-xs text-muted-foreground">{trace.span_count}</span>

                {/* Status */}
                <div className="flex items-center gap-1.5">
                  {trace.has_errors ? (
                    <>
                      <span className="h-2 w-2 rounded-full bg-destructive shrink-0" />
                      <span className="text-xs text-destructive">{trace.error_count} err</span>
                    </>
                  ) : (
                    <>
                      <span className="h-2 w-2 rounded-full bg-success shrink-0" />
                      <span className="text-xs text-success">OK</span>
                    </>
                  )}
                </div>

                {/* Relative time */}
                <span className="text-xs text-muted-foreground">
                  {relativeTime(trace.start_time)}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
