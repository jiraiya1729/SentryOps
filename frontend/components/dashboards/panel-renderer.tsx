"use client"

import { useState, useEffect } from "react"
import { X } from "lucide-react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { executePanelQuery } from "@/lib/api/dashboards"
import type { DashboardPanel, PanelQueryResponse } from "@/lib/types/api"
import { CHART_COLORS, CHART_GRID_COLOR, CHART_AXIS_COLOR, CHART_TOOLTIP_STYLE } from "@/lib/chart-colors"

interface PanelRendererProps {
  panel: DashboardPanel
  timeRange: string
  editMode: boolean
  onRemove: () => void
}

function formatBytes(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} GB`
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)} MB`
  if (v >= 1e3) return `${(v / 1e3).toFixed(2)} KB`
  return `${v.toFixed(2)} B`
}

function formatValue(v: number, format?: unknown): string {
  if (format === "bytes") return formatBytes(v)
  if (format === "percent") return `${v.toFixed(1)}%`
  return v.toLocaleString()
}

function seriesToChartData(
  series: Record<string, { time: string; value: number }[]>
): { data: Record<string, number | string>[]; keys: string[] } {
  const map = new Map<string, Record<string, number | string>>()
  for (const [label, points] of Object.entries(series)) {
    for (const pt of points) {
      if (!map.has(pt.time)) map.set(pt.time, { time: pt.time })
      map.get(pt.time)![label] = pt.value
    }
  }
  const data = [...map.values()].sort((a, b) =>
    String(a.time) < String(b.time) ? -1 : 1
  )
  return { data, keys: Object.keys(series) }
}

function levelVariant(level: string): "destructive" | "secondary" | "outline" {
  if (level === "error" || level === "critical") return "destructive"
  if (level === "warning" || level === "warn") return "secondary"
  return "outline"
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

export function PanelRenderer({ panel, timeRange, editMode, onRemove }: PanelRendererProps) {
  const [data, setData] = useState<PanelQueryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    executePanelQuery(panel.panel_type, panel.query_config, timeRange)
      .then((res) => { if (!cancelled) { setData(res); setLoading(false) } })
      .catch((e) => { if (!cancelled) { setError(String(e)); setLoading(false) } })
    return () => { cancelled = true }
  }, [panel.id, panel.panel_type, timeRange])

  return (
    <div className={editMode ? "relative ring-2 ring-dashed ring-border rounded-xl" : "relative"}>
      {editMode && (
        <button
          onClick={onRemove}
          className="absolute top-2 right-2 z-10 flex items-center justify-center w-5 h-5 rounded-full bg-destructive text-destructive-foreground hover:opacity-80 transition-opacity"
        >
          <X className="h-3 w-3" />
        </button>
      )}
      <Card className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{panel.title}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-48 w-full rounded" />
          ) : error ? (
            <p className="text-xs text-muted-foreground py-4 text-center">{error}</p>
          ) : (
            <PanelContent panel={panel} data={data!} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function PanelContent({ panel, data }: { panel: DashboardPanel; data: PanelQueryResponse }) {
  if (panel.panel_type === "stat_card") {
    const v = data.value ?? 0
    return (
      <div className="flex flex-col items-center justify-center py-6 gap-1">
        <p className="text-3xl font-bold tabular-nums">
          {formatValue(v, panel.display_config.format)}
        </p>
        <p className="text-xs text-muted-foreground">{panel.title}</p>
      </div>
    )
  }

  if (panel.panel_type === "metric_chart") {
    const { data: chartData, keys } = seriesToChartData(data.series ?? {})
    if (keys.length === 0) {
      return <p className="text-xs text-muted-foreground py-4 text-center">No data</p>
    }
    return (
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} opacity={0.6} />
          <XAxis
            dataKey="time"
            stroke={CHART_AXIS_COLOR}
            fontSize={10}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: string) => new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            interval="preserveStartEnd"
          />
          <YAxis stroke={CHART_AXIS_COLOR} fontSize={10} tickLine={false} axisLine={false} width={40} />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            labelStyle={{ color: "#78716c" }}
          />
          {keys.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  if (panel.panel_type === "log_table") {
    const logs = data.logs ?? []
    if (logs.length === 0) {
      return <p className="text-xs text-muted-foreground py-4 text-center">No logs</p>
    }
    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs w-24">Time</TableHead>
            <TableHead className="text-xs w-16">Level</TableHead>
            <TableHead className="text-xs">Message</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log, i) => (
            <TableRow key={i}>
              <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                {new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </TableCell>
              <TableCell>
                <Badge variant={levelVariant(log.level)} className="text-xs px-1 py-0">
                  {log.level}
                </Badge>
              </TableCell>
              <TableCell className="text-xs max-w-xs truncate">{log.message}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )
  }

  if (panel.panel_type === "event_list") {
    const events = data.events ?? []
    if (events.length === 0) {
      return <p className="text-xs text-muted-foreground py-4 text-center">No events</p>
    }
    return (
      <div className="space-y-2">
        {events.map((ev, i) => (
          <div key={i} className="flex items-start justify-between gap-2 text-xs border-b border-border pb-2 last:border-0">
            <div className="min-w-0">
              <p className="font-medium">{ev.reason}</p>
              <p className="text-muted-foreground truncate">{ev.message}</p>
              <p className="text-muted-foreground/60">{ev.namespace} / {ev.resource}</p>
            </div>
            <span className="text-muted-foreground whitespace-nowrap shrink-0">{relativeTime(ev.timestamp)}</span>
          </div>
        ))}
      </div>
    )
  }

  return <p className="text-xs text-muted-foreground py-4 text-center">Unknown panel type</p>
}
