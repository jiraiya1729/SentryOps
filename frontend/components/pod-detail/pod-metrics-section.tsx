"use client"

import { useState, useEffect, useCallback, useRef } from "react"
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
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartTooltip } from "@/components/metrics/chart-tooltip"
import { getPodMetricsDetail } from "@/lib/api/metrics"
import type { MetricDatapoint } from "@/lib/types/api"

const TIME_RANGES = ["1h", "6h", "24h"] as const

interface PodMetricsSectionProps {
  namespace: string
  name: string
}

function formatTime(tick: string) {
  return new Date(tick).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function formatMillicores(value: number) {
  if (value >= 1) return `${value.toFixed(2)}`
  return `${(value * 1000).toFixed(0)}m`
}

function formatBytes(bytes: number) {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(0)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

export function PodMetricsSection({ namespace, name }: PodMetricsSectionProps) {
  const [timeRange, setTimeRange] = useState<string>("1h")
  const [cpuData, setCpuData] = useState<MetricDatapoint[]>([])
  const [memoryData, setMemoryData] = useState<MetricDatapoint[]>([])
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await getPodMetricsDetail(namespace, name, timeRange)
      setCpuData(res.metrics["cpu_usage_cores"] || [])
      setMemoryData(res.metrics["memory_usage_bytes"] || [])
    } catch {
      // Keep previous data
    } finally {
      setLoading(false)
    }
  }, [namespace, name, timeRange])

  useEffect(() => {
    setLoading(true)
    fetchData()
    intervalRef.current = setInterval(fetchData, 15000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchData])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Metrics</h2>
        <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
          {TIME_RANGES.map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? "default" : "ghost"}
              size="xs"
              onClick={() => setTimeRange(range)}
            >
              {range}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-52 rounded-lg" />
          <Skeleton className="h-52 rounded-lg" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium text-muted-foreground">CPU</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={cpuData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3c4753" opacity={0.4} />
                  <XAxis dataKey="timestamp" tickFormatter={formatTime} stroke="#6b7280" fontSize={10} tickLine={false} />
                  <YAxis tickFormatter={formatMillicores} stroke="#6b7280" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip content={<ChartTooltip formatValue={formatMillicores} />} />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium text-muted-foreground">Memory</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={memoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3c4753" opacity={0.4} />
                  <XAxis dataKey="timestamp" tickFormatter={formatTime} stroke="#6b7280" fontSize={10} tickLine={false} />
                  <YAxis tickFormatter={formatBytes} stroke="#6b7280" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip content={<ChartTooltip formatValue={formatBytes} />} />
                  <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
