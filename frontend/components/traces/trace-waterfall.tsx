"use client"

import { useState, useMemo } from "react"
import type { TraceDetail, Span } from "@/lib/types/api"
import { getServiceColor, formatDuration } from "@/lib/traces-utils"
import { SpanDetailPanel } from "./span-detail-panel"

interface FlatSpan {
  span: Span
  depth: number
}

function buildFlatTree(spans: Span[]): FlatSpan[] {
  const children = new Map<string | null, Span[]>()
  for (const span of spans) {
    const key = span.parent_span_id ?? null
    if (!children.has(key)) children.set(key, [])
    children.get(key)!.push(span)
  }

  const result: FlatSpan[] = []

  function dfs(spanId: string | null, depth: number) {
    const kids = children.get(spanId) ?? []
    for (const span of kids) {
      result.push({ span, depth })
      dfs(span.span_id, depth + 1)
    }
  }

  dfs(null, 0)
  // Fallback: if tree building left some spans out (orphaned), append them flat
  const seen = new Set(result.map((f) => f.span.span_id))
  for (const span of spans) {
    if (!seen.has(span.span_id)) result.push({ span, depth: 0 })
  }

  return result
}

interface Props {
  trace: TraceDetail
}

export function TraceWaterfall({ trace }: Props) {
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null)

  const flatSpans = useMemo(() => buildFlatTree(trace.spans), [trace.spans])

  const traceStartMs = useMemo(() => {
    const times = trace.spans.map((s) => new Date(s.timestamp).getTime())
    return times.length ? Math.min(...times) : 0
  }, [trace.spans])

  const traceDurationMs = useMemo(() => {
    const ends = trace.spans.map(
      (s) => new Date(s.timestamp).getTime() - traceStartMs + s.duration_ms
    )
    return Math.max(...ends, 1)
  }, [trace.spans, traceStartMs])

  const tickValues = [0, 25, 50, 75, 100]

  // Service legend
  const uniqueServices = useMemo(
    () => [...new Set(trace.spans.map((s) => s.service_name))],
    [trace.spans]
  )

  return (
    <div className="space-y-4">
      {/* Service legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {uniqueServices.map((svc) => (
          <div key={svc} className="flex items-center gap-1.5">
            <span
              className="h-3 w-3 rounded-sm shrink-0"
              style={{ backgroundColor: getServiceColor(svc) }}
            />
            <span className="text-xs text-muted-foreground">{svc}</span>
          </div>
        ))}
      </div>

      <div className={`flex gap-0 rounded-lg border border-border overflow-hidden`}>
        {/* Waterfall */}
        <div className={`${selectedSpan ? "w-3/5" : "w-full"} overflow-x-auto`}>
          {/* Header: axis ticks */}
          <div className="flex bg-muted/50 border-b border-border h-9">
            <div className="w-2/5 shrink-0 px-4 flex items-center">
              <span className="text-xs font-medium text-muted-foreground">Span</span>
            </div>
            <div className="flex-1 relative flex items-center">
              {tickValues.map((pct) => (
                <div
                  key={pct}
                  className="absolute flex flex-col items-center"
                  style={{ left: `${pct}%` }}
                >
                  <span className="text-[10px] text-muted-foreground/60 translate-x-[-50%]">
                    {pct === 0
                      ? "0"
                      : formatDuration((traceDurationMs * pct) / 100)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Rows */}
          {flatSpans.map(({ span, depth }) => {
            const spanStartMs = new Date(span.timestamp).getTime() - traceStartMs
            const leftPct = (spanStartMs / traceDurationMs) * 100
            const widthPct = Math.max(
              (2 / traceDurationMs) * 100,
              (span.duration_ms / traceDurationMs) * 100
            )
            const color = getServiceColor(span.service_name)
            const isError = span.status_code === "ERROR"
            const isSelected = selectedSpan?.span_id === span.span_id

            return (
              <div
                key={span.span_id}
                onClick={() => setSelectedSpan(isSelected ? null : span)}
                className={`flex border-b border-border/50 h-9 cursor-pointer transition-colors ${
                  isSelected ? "bg-muted/50" : "hover:bg-muted/20"
                }`}
              >
                {/* Label */}
                <div
                  className="w-2/5 shrink-0 flex items-center px-2 overflow-hidden"
                  style={{ paddingLeft: `${8 + depth * 16}px` }}
                >
                  <span
                    className="h-2 w-2 rounded-full shrink-0 mr-2"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs truncate">{span.operation_name}</span>
                </div>

                {/* Bar */}
                <div className="flex-1 relative flex items-center">
                  <div
                    className={`absolute h-4 rounded-sm ${isError ? "ring-1 ring-destructive/60" : ""}`}
                    style={{
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                      backgroundColor: color,
                      opacity: isError ? 0.9 : 0.7,
                    }}
                  />
                  <span
                    className="absolute text-[10px] text-muted-foreground whitespace-nowrap"
                    style={{ left: `calc(${leftPct}% + ${widthPct}% + 4px)` }}
                  >
                    {formatDuration(span.duration_ms)}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Side panel */}
        {selectedSpan && (
          <div className="w-2/5 shrink-0 border-l border-border overflow-hidden">
            <SpanDetailPanel
              span={selectedSpan}
              traceStartMs={traceStartMs}
              onClose={() => setSelectedSpan(null)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
