"use client"

import { useState, useEffect, useRef } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useDebounce } from "@/hooks/use-debounce"
import { useLogStream } from "@/hooks/use-log-stream"
import { searchLogs, getLogStats } from "@/lib/api/logs"
import type { LogEntry, LogStatEntry } from "@/lib/types/api"
import { LogFilters } from "./log-filters"
import { LogHistogram } from "./log-histogram"
import { LogList } from "./log-list"

export function LogViewer() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const qParam = searchParams.get("q") ?? ""
  const namespaceParam = searchParams.get("namespace") ?? ""
  const podParam = searchParams.get("pod") ?? ""
  const levelParam = searchParams.get("level") ?? ""
  const sinceParam = searchParams.get("since") ?? ""
  const untilParam = searchParams.get("until") ?? ""

  const [localSearch, setLocalSearch] = useState(qParam)
  const [localPod, setLocalPod] = useState(podParam)
  const debouncedSearch = useDebounce(localSearch, 300)
  const debouncedPod = useDebounce(localPod, 300)

  const [logs, setLogs] = useState<LogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<LogStatEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdatedText, setLastUpdatedText] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [liveMode, setLiveMode] = useState(false)
  const [namespaceOptions, setNamespaceOptions] = useState<string[]>([])
  const [timeRange, setTimeRange] = useState<number | null>(() => {
    if (sinceParam) {
      const diff = Math.round((Date.now() - new Date(sinceParam).getTime()) / 60000)
      const presets = [15, 60, 360, 1440, 10080]
      return presets.find((p) => Math.abs(p - diff) < 2) ?? null
    }
    return null
  })

  const [fetchTrigger, setFetchTrigger] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastFetchTimeRef = useRef<number | null>(null)

  const levels = levelParam ? levelParam.split(",") : []

  const {
    logs: streamLogs,
    isConnected,
    droppedCount,
    linesPerSecond,
  } = useLogStream({
    enabled: liveMode,
    namespace: namespaceParam || undefined,
    pod: podParam || undefined,
    level: levelParam || undefined,
  })

  function handleLiveModeToggle() {
    setLiveMode((prev) => {
      if (prev) {
        setFetchTrigger((n) => n + 1)
      } else {
        setAutoRefresh(false)
      }
      return !prev
    })
  }

  function updateURL(updates: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString())
    for (const [key, value] of Object.entries(updates)) {
      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
    }
    router.replace(`/cluster/logs?${params.toString()}`, { scroll: false })
  }

  useEffect(() => {
    if (debouncedSearch !== qParam) {
      updateURL({ q: debouncedSearch })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  useEffect(() => {
    if (debouncedPod !== podParam) {
      updateURL({ pod: debouncedPod })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedPod])

  useEffect(() => {
    let cancelled = false

    let since = sinceParam
    let until = untilParam
    if (timeRange) {
      const now = new Date()
      since = new Date(now.getTime() - timeRange * 60000).toISOString()
      until = now.toISOString()
    }

    const params = {
      q: qParam || undefined,
      namespace: namespaceParam || undefined,
      pod: podParam || undefined,
      level: levelParam || undefined,
      since: since || undefined,
      until: until || undefined,
      limit: 100,
      direction: "backward" as const,
    }

    Promise.all([
      searchLogs(params),
      getLogStats({
        q: params.q,
        namespace: params.namespace,
        pod: params.pod,
        level: params.level,
        since: params.since,
        until: params.until,
      }),
    ])
      .then(([logsRes, statsRes]) => {
        if (cancelled) return
        setError(null)
        setLogs(logsRes.logs)
        setTotal(logsRes.total)
        setStats(statsRes)
        setLastUpdatedText("just now")
        lastFetchTimeRef.current = Date.now()

        const uniqueNs = [...new Set(logsRes.logs.map((l) => l.namespace))]
        setNamespaceOptions((prev) => {
          const merged = [...new Set([...prev, ...uniqueNs])]
          return merged.sort()
        })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : "Failed to fetch logs")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [qParam, namespaceParam, podParam, levelParam, sinceParam, untilParam, timeRange, fetchTrigger])

  useEffect(() => {
    const timer = setInterval(() => {
      if (lastFetchTimeRef.current === null) return
      const seconds = Math.floor((Date.now() - lastFetchTimeRef.current) / 1000)
      if (seconds < 5) setLastUpdatedText("just now")
      else if (seconds < 60) setLastUpdatedText(`${seconds}s ago`)
      else setLastUpdatedText(`${Math.floor(seconds / 60)}m ago`)
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        setFetchTrigger((n) => n + 1)
      }, 10_000)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [autoRefresh])

  function handleNamespaceChange(ns: string) {
    updateURL({ namespace: ns })
  }

  function handleLevelsChange(newLevels: string[]) {
    updateURL({ level: newLevels.join(",") })
  }

  function handleTimeRangeChange(minutes: number | null) {
    setTimeRange(minutes)
    if (minutes) {
      const now = new Date()
      const since = new Date(now.getTime() - minutes * 60000)
      updateURL({ since: since.toISOString(), until: now.toISOString() })
    } else {
      updateURL({ since: "", until: "" })
    }
  }

  return (
    <div className="space-y-4">
      <LogFilters
        search={localSearch}
        onSearchChange={setLocalSearch}
        namespace={namespaceParam}
        onNamespaceChange={handleNamespaceChange}
        pod={localPod}
        onPodChange={setLocalPod}
        levels={levels}
        onLevelsChange={handleLevelsChange}
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
        autoRefresh={autoRefresh}
        onAutoRefreshToggle={() => setAutoRefresh((v) => !v)}
        lastUpdatedText={lastUpdatedText}
        namespaceOptions={namespaceOptions}
        liveMode={liveMode}
        onLiveModeToggle={handleLiveModeToggle}
        isConnected={isConnected}
        linesPerSecond={linesPerSecond}
      />

      {!liveMode && (
        <LogHistogram buckets={stats} isLoading={isLoading && stats.length === 0} />
      )}

      {liveMode && droppedCount > 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-2 text-sm text-yellow-200 flex items-center gap-2">
          <span className="font-medium">{droppedCount} lines dropped</span>
          <span className="text-muted-foreground">(high throughput)</span>
        </div>
      )}

      {liveMode && !isConnected && streamLogs.length === 0 && (
        <div className="rounded-lg border border-border bg-muted/30 p-8 flex flex-col items-center justify-center gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-yellow-500" />
            </span>
            <span className="text-sm text-muted-foreground font-medium">Connecting to log stream...</span>
          </div>
        </div>
      )}

      {error && !liveMode ? (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : (
        <LogList
          logs={liveMode ? streamLogs : logs}
          total={liveMode ? streamLogs.length : total}
          isLoading={!liveMode && isLoading && logs.length === 0}
          liveMode={liveMode}
        />
      )}
    </div>
  )
}
