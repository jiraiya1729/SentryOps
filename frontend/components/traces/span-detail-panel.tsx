"use client"

import type { Span } from "@/lib/types/api"
import { getServiceColor, formatDuration } from "@/lib/traces-utils"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  span: Span
  traceStartMs: number
  onClose: () => void
}

function KVRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null
  return (
    <div className="flex gap-2 py-1.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted-foreground w-32 shrink-0">{label}</span>
      <span className="text-xs font-mono break-all">{String(value)}</span>
    </div>
  )
}

export function SpanDetailPanel({ span, traceStartMs, onClose }: Props) {
  const startOffset = new Date(span.timestamp).getTime() - traceStartMs

  let attributes: Record<string, unknown> = {}
  try {
    if (span.attributes_json) attributes = JSON.parse(span.attributes_json)
  } catch {}

  let events: Array<{ name: string; timestamp: string; attributes?: Record<string, unknown> }> = []
  try {
    if (span.events_json) events = JSON.parse(span.events_json)
  } catch {}

  const statusColor =
    span.status_code === "ERROR"
      ? "text-destructive bg-destructive/10 border-destructive/20"
      : span.status_code === "OK"
      ? "text-success bg-success/10 border-success/20"
      : "text-muted-foreground bg-muted border-border"

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-4 border-b border-border">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="h-2.5 w-2.5 rounded-full shrink-0"
              style={{ backgroundColor: getServiceColor(span.service_name) }}
            />
            <span className="text-sm font-medium">{span.service_name}</span>
            <span
              className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${statusColor}`}
            >
              {span.status_code}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground truncate">{span.operation_name}</p>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} className="shrink-0">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="p-4 space-y-4">
        {/* Timing */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
            Timing
          </p>
          <div>
            <KVRow label="Duration" value={formatDuration(span.duration_ms)} />
            <KVRow label="Start offset" value={formatDuration(startOffset)} />
            <KVRow label="Timestamp" value={span.timestamp} />
            <KVRow label="Span kind" value={span.span_kind} />
          </div>
        </section>

        {/* IDs */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
            IDs
          </p>
          <div>
            <KVRow label="Span ID" value={span.span_id} />
            <KVRow label="Parent span" value={span.parent_span_id} />
            <KVRow label="Trace ID" value={span.trace_id} />
          </div>
        </section>

        {/* HTTP */}
        {(span.http_method || span.http_url || span.http_status_code) && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
              HTTP
            </p>
            <div>
              <KVRow label="Method" value={span.http_method} />
              <KVRow label="URL" value={span.http_url} />
              <KVRow label="Status code" value={span.http_status_code} />
            </div>
          </section>
        )}

        {/* DB */}
        {(span.db_system || span.db_statement) && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Database
            </p>
            <div>
              <KVRow label="System" value={span.db_system} />
              <KVRow label="Statement" value={span.db_statement} />
            </div>
          </section>
        )}

        {/* Resource */}
        {(span.namespace || span.pod_name) && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Resource
            </p>
            <div>
              <KVRow label="Namespace" value={span.namespace} />
              <KVRow label="Pod" value={span.pod_name} />
            </div>
          </section>
        )}

        {/* Attributes */}
        {Object.keys(attributes).length > 0 && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Attributes
            </p>
            <div>
              {Object.entries(attributes).map(([k, v]) => (
                <KVRow key={k} label={k} value={String(v)} />
              ))}
            </div>
          </section>
        )}

        {/* Events */}
        {events.length > 0 && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Events
            </p>
            <div className="space-y-2">
              {events.map((ev, i) => (
                <div key={i} className="rounded-md border border-border bg-muted/30 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium">{ev.name}</span>
                    <span className="text-xs text-muted-foreground">{ev.timestamp}</span>
                  </div>
                  {ev.attributes && Object.keys(ev.attributes).length > 0 && (
                    <div className="mt-1">
                      {Object.entries(ev.attributes).map(([k, v]) => (
                        <div key={k} className="flex gap-2 text-xs">
                          <span className="text-muted-foreground w-24 shrink-0">{k}</span>
                          <span className="font-mono break-all">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
