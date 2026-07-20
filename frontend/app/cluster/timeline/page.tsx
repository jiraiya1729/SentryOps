"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts"
import { getTimeline } from "@/lib/api/deployments"
import type { TimelineData, TimelineDeployment, TimelineIncident } from "@/lib/types/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"

const HOURS_OPTIONS = [
  { label: "6h", value: 6 },
  { label: "24h", value: 24 },
  { label: "7d", value: 168 },
]

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  info: "#6b7280",
}

const HEALTH_DOT_COLOR = (score: number, status: string) => {
  if (status === "failed") return "#ef4444"
  if (status === "degraded") return "#eab308"
  if (status === "healthy") return "#22c55e"
  return "#6b7280"
}

function DeployMarker({ d, onClick }: { d: TimelineDeployment; onClick: () => void }) {
  const color = HEALTH_DOT_COLOR(d.health_score, d.status)
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-center gap-1"
      title={`${d.deployment_name}\n${d.author}\nHealth: ${d.health_score}`}
    >
      <div
        className="w-3 h-3 rounded-full border-2 border-background transition-transform group-hover:scale-125"
        style={{ backgroundColor: color }}
      />
      <span className="text-[9px] text-muted-foreground group-hover:text-foreground max-w-[60px] truncate leading-tight">
        {d.deployment_name}
      </span>
    </button>
  )
}

function IncidentMarker({ inc, onClick }: { inc: TimelineIncident; onClick: () => void }) {
  const color = SEVERITY_COLOR[inc.severity] ?? "#6b7280"
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-center gap-1"
      title={`${inc.severity.toUpperCase()}: ${inc.summary}`}
    >
      <div
        className="w-3 h-3 rotate-45 border-2 border-background transition-transform group-hover:scale-125"
        style={{ backgroundColor: color }}
      />
      <span className="text-[9px] text-muted-foreground group-hover:text-foreground max-w-[60px] truncate leading-tight">
        {inc.severity}
      </span>
    </button>
  )
}

export default function TimelinePage() {
  const router = useRouter()
  const [data, setData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(true)
  const [hours, setHours] = useState(24)
  const [namespace, setNamespace] = useState("")

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getTimeline({
        hours,
        namespace: namespace || undefined,
      })
      setData(result)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [hours, namespace])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Deployment Timeline</h1>
        <p className="text-sm text-muted-foreground">
          Visualize deployments, incidents, and metric trends together
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center rounded-md border border-border overflow-hidden">
          {HOURS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setHours(opt.value)}
              className={`px-3 py-1.5 text-xs transition-colors ${
                hours === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Namespace filter"
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-40"
        />
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full rounded-lg" />
          <Skeleton className="h-20 w-full rounded-lg" />
          <Skeleton className="h-32 w-full rounded-lg" />
        </div>
      ) : !data ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-2">
          <p className="text-sm">Failed to load timeline data</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Deployments swim lane */}
          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Deployments</span>
              <Badge variant="outline" className="text-xs">{data.deployments.length}</Badge>
            </div>
            {data.deployments.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No deployments in this window</p>
            ) : (
              <div className="flex items-end gap-4 overflow-x-auto pb-2 min-h-[56px]">
                {data.deployments.map((d) => (
                  <DeployMarker
                    key={d.id}
                    d={d}
                    onClick={() => router.push(`/cluster/deployments/${d.id}`)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Incidents swim lane */}
          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Incidents</span>
              <Badge variant="outline" className="text-xs">{data.incidents.length}</Badge>
            </div>
            {data.incidents.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No incidents in this window</p>
            ) : (
              <div className="flex items-end gap-4 overflow-x-auto pb-2 min-h-[56px]">
                {data.incidents.map((inc) => (
                  <IncidentMarker
                    key={inc.investigation_id}
                    inc={inc}
                    onClick={() => router.push(`/cluster/guardian?investigation=${inc.investigation_id}`)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Metrics swim lane */}
          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Error Rate Trend</span>
            </div>
            {data.metrics_summary.error_rate.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4">No metric data in this window</p>
            ) : (
              <ResponsiveContainer width="100%" height={100}>
                <LineChart data={data.metrics_summary.error_rate}>
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis hide />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                    labelFormatter={(v) => new Date(v as string).toLocaleString()}
                  />
                  {data.deployments.map((d) => (
                    <ReferenceLine
                      key={d.id}
                      x={d.timestamp}
                      stroke={HEALTH_DOT_COLOR(d.health_score, d.status)}
                      strokeDasharray="3 3"
                      strokeOpacity={0.5}
                    />
                  ))}
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#6b7280"
                    strokeWidth={1.5}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
              <span>Healthy deploy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
              <span>Degraded deploy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>Failed deploy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rotate-45 bg-orange-500" />
              <span>Incident</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
