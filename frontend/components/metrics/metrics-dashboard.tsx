"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { queryMetrics, getMetricsSummary } from "@/lib/api/metrics"
import { getNamespaces } from "@/lib/api/namespaces"
import type {
  MetricSeries,
  MetricsSummaryResponse,
  Namespace,
} from "@/lib/types/api"
import { MetricsFilters } from "./metrics-filters"
import { CpuChart } from "./cpu-chart"
import { MemoryChart } from "./memory-chart"
import { Skeleton } from "@/components/ui/skeleton"

function seriesToChartData(series: MetricSeries[]): {
  data: Record<string, number | string>[]
  keys: string[]
} {
  const timestampMap = new Map<string, Record<string, number | string>>()
  const keys: string[] = []

  for (const s of series) {
    const key = Object.values(s.labels)[0] || "unknown"
    if (!keys.includes(key)) keys.push(key)
    for (const dp of s.datapoints) {
      if (!timestampMap.has(dp.timestamp)) {
        timestampMap.set(dp.timestamp, { timestamp: dp.timestamp })
      }
      timestampMap.get(dp.timestamp)![key] = dp.value
    }
  }

  const data = Array.from(timestampMap.values()).sort(
    (a, b) => new Date(a.timestamp as string).getTime() - new Date(b.timestamp as string).getTime()
  )

  return { data, keys }
}

function topNSeries(series: MetricSeries[], n: number): MetricSeries[] {
  return series
    .map((s) => ({
      ...s,
      lastValue: s.datapoints.length > 0 ? s.datapoints[s.datapoints.length - 1].value : 0,
    }))
    .sort((a, b) => b.lastValue - a.lastValue)
    .slice(0, n)
}

export function MetricsDashboard() {
  const [timeRange, setTimeRange] = useState("1h")
  const [namespace, setNamespace] = useState("")
  const [namespaces, setNamespaces] = useState<Namespace[]>([])
  const [cpuSeries, setCpuSeries] = useState<MetricSeries[]>([])
  const [memorySeries, setMemorySeries] = useState<MetricSeries[]>([])
  const [summary, setSummary] = useState<MetricsSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [cpuRes, memRes, summaryRes] = await Promise.all([
        queryMetrics({
          metric: "cpu_usage_cores",
          namespace: namespace || undefined,
          since: timeRange,
          group_by: "pod",
        }),
        queryMetrics({
          metric: "memory_usage_bytes",
          namespace: namespace || undefined,
          since: timeRange,
          group_by: "pod",
        }),
        getMetricsSummary(namespace || undefined),
      ])

      setCpuSeries(topNSeries(cpuRes.series, 5))
      setMemorySeries(topNSeries(memRes.series, 5))
      setSummary(summaryRes)
      setLastUpdated(new Date())
    } catch {
      // Keep previous data on error
    } finally {
      setLoading(false)
    }
  }, [timeRange, namespace])

  useEffect(() => {
    getNamespaces().then((res) => setNamespaces(res.items)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchData()

    intervalRef.current = setInterval(fetchData, 15000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchData])

  const cpuChart = seriesToChartData(cpuSeries)
  const memChart = seriesToChartData(memorySeries)

  return (
    <div className="space-y-4">
      <MetricsFilters
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
        namespace={namespace}
        onNamespaceChange={setNamespace}
        namespaces={namespaces}
        lastUpdated={lastUpdated}
      />

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-80 rounded-lg" />
          <Skeleton className="h-80 rounded-lg" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CpuChart data={cpuChart.data} series={cpuChart.keys} />
          <MemoryChart data={memChart.data} series={memChart.keys} />
        </div>
      )}

      {!loading && summary && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TopPodsCard
            title="Top CPU Consumers"
            items={summary.top_cpu.map((p) => ({
              namespace: p.namespace,
              pod: p.pod,
              value: `${(p.cpu_cores * 1000).toFixed(0)}m`,
            }))}
          />
          <TopPodsCard
            title="Top Memory Consumers"
            items={summary.top_memory.map((p) => ({
              namespace: p.namespace,
              pod: p.pod,
              value: formatBytes(p.memory_bytes),
            }))}
          />
        </div>
      )}
    </div>
  )
}

function formatBytes(bytes: number) {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(0)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

function TopPodsCard({
  title,
  items,
}: {
  title: string
  items: { namespace: string; pod: string; value: string }[]
}) {
  if (!items.length) return null

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-medium mb-3">{title}</h3>
      <div className="space-y-2">
        {items.slice(0, 5).map((item, i) => (
          <div key={`${item.namespace}/${item.pod}`} className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground w-4">{i + 1}.</span>
            <span className="text-muted-foreground truncate flex-1">
              {item.namespace}/{item.pod}
            </span>
            <span className="font-mono font-medium">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
