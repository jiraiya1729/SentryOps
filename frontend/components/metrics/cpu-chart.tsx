"use client"

import { useState, useCallback } from "react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "./chart-tooltip"
import { EmptyState } from "@/components/shared/empty-state"
import { CHART_COLORS, CHART_GRID_COLOR, CHART_AXIS_COLOR } from "@/lib/chart-colors"

interface CpuChartProps {
  data: Record<string, number | string>[]
  series: string[]
  cpuRequest?: number
  cpuLimit?: number
  onZoom?: (left: string, right: string) => void
}

function formatTime(tick: string) {
  const d = new Date(tick)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function formatMillicores(value: number) {
  if (value >= 1) return `${value.toFixed(2)} cores`
  return `${(value * 1000).toFixed(0)}m`
}

export function CpuChart({ data, series, cpuRequest, cpuLimit, onZoom }: CpuChartProps) {
  const [refAreaLeft, setRefAreaLeft] = useState<string | null>(null)
  const [refAreaRight, setRefAreaRight] = useState<string | null>(null)

  const handleMouseDown = useCallback((e: Record<string, unknown>) => {
    if (e?.activeLabel) setRefAreaLeft(String(e.activeLabel))
  }, [])

  const handleMouseMove = useCallback(
    (e: Record<string, unknown>) => {
      if (refAreaLeft && e?.activeLabel) setRefAreaRight(String(e.activeLabel))
    },
    [refAreaLeft]
  )

  const handleMouseUp = useCallback(() => {
    if (refAreaLeft && refAreaRight && onZoom) {
      const [left, right] =
        refAreaLeft < refAreaRight
          ? [refAreaLeft, refAreaRight]
          : [refAreaRight, refAreaLeft]
      onZoom(left, right)
    }
    setRefAreaLeft(null)
    setRefAreaRight(null)
  }, [refAreaLeft, refAreaRight, onZoom])

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState title="No CPU data" message="No metrics collected yet." />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_COLOR} opacity={0.6} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke={CHART_AXIS_COLOR}
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatMillicores}
              stroke={CHART_AXIS_COLOR}
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              content={<ChartTooltip formatValue={formatMillicores} />}
            />
            {series.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={CHART_COLORS[i % CHART_COLORS.length]}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />
            ))}
            {cpuRequest !== undefined && (
              <ReferenceLine
                y={cpuRequest}
                stroke="#7c3aed"
                strokeDasharray="5 5"
                strokeWidth={1}
                label={{ value: "request", position: "right", fill: "#7c3aed", fontSize: 10 }}
              />
            )}
            {cpuLimit !== undefined && (
              <ReferenceLine
                y={cpuLimit}
                stroke="#dc2626"
                strokeDasharray="5 5"
                strokeWidth={1}
                label={{ value: "limit", position: "right", fill: "#dc2626", fontSize: 10 }}
              />
            )}
            {refAreaLeft && refAreaRight && (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                strokeOpacity={0.3}
                fill="#7c3aed"
                fillOpacity={0.1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
