"use client"

import { useEffect, useState, useCallback } from "react"
import { getChanges, getChangesSummary } from "@/lib/api/changes"
import type { Change, ChangeSummaryItem } from "@/lib/api/changes"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

const SINCE_OPTIONS = [
  { label: "1h", value: "1h" },
  { label: "6h", value: "6h" },
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
]

const CHANGE_TYPE_COLORS: Record<string, string> = {
  modified: "text-yellow-800 bg-yellow-50 border-yellow-200",
  discovered: "text-violet-700 bg-violet-50 border-violet-200",
  deleted: "text-red-700 bg-red-50 border-red-200",
}

function ChangeBadge({ type }: { type: string }) {
  const cls = CHANGE_TYPE_COLORS[type] ?? "text-muted-foreground bg-muted border-border"
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {type}
    </span>
  )
}

function formatTime(ts: string | null) {
  if (!ts) return "—"
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function SummaryCards({ items }: { items: ChangeSummaryItem[] }) {
  const totals: Record<string, number> = {}
  for (const item of items) {
    totals[item.resource_kind] = (totals[item.resource_kind] ?? 0) + item.count
  }
  const kinds = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 6)

  if (kinds.length === 0) {
    return <p className="text-sm text-muted-foreground">No changes in this window.</p>
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {kinds.map(([kind, count]) => (
        <div key={kind} className="rounded-lg border border-border bg-card p-3 space-y-1">
          <p className="text-xs text-muted-foreground truncate">{kind}</p>
          <p className="text-2xl font-semibold tabular-nums">{count}</p>
          <p className="text-xs text-muted-foreground">changes</p>
        </div>
      ))}
    </div>
  )
}

export default function ChangesPage() {
  const [since, setSince] = useState("6h")
  const [namespaceFilter, setNamespaceFilter] = useState("")
  const [kindFilter, setKindFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")

  const [changes, setChanges] = useState<Change[]>([])
  const [summary, setSummary] = useState<ChangeSummaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [changesRes, summaryRes] = await Promise.all([
        getChanges({
          since,
          namespace: namespaceFilter || undefined,
          resource_kind: kindFilter || undefined,
          change_type: typeFilter || undefined,
          limit: 100,
        }),
        getChangesSummary({ since, namespace: namespaceFilter || undefined }),
      ])
      setChanges(changesRes.changes)
      setSummary(summaryRes.summary)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [since, namespaceFilter, kindFilter, typeFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Resource Changes</h1>
        <p className="text-sm text-muted-foreground">
          Track modifications, discoveries, and deletions across your cluster
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center rounded-md border border-border overflow-hidden">
          {SINCE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSince(opt.value)}
              className={`px-3 py-1.5 text-xs transition-colors ${
                since === opt.value
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
          placeholder="Namespace"
          value={namespaceFilter}
          onChange={(e) => setNamespaceFilter(e.target.value)}
          className="h-8 w-36 rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <input
          type="text"
          placeholder="Kind (e.g. Deployment)"
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value)}
          className="h-8 w-44 rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All types</option>
          <option value="modified">Modified</option>
          <option value="discovered">Discovered</option>
          <option value="deleted">Deleted</option>
        </select>
      </div>

      {/* Summary cards */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[76px] rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">Failed to load changes. Is the backend running?</p>
      ) : (
        <SummaryCards items={summary} />
      )}

      {/* Changes table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="grid grid-cols-[1fr_auto_auto_auto_2fr] items-center gap-4 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground uppercase tracking-wide">
          <span>Resource</span>
          <span>Kind</span>
          <span>Namespace</span>
          <span>Type</span>
          <span>Summary</span>
        </div>

        {loading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_auto_auto_2fr] items-center gap-4 px-4 py-3 border-t border-border">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-20 rounded-md" />
              <Skeleton className="h-4 w-full" />
            </div>
          ))
        ) : changes.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-muted-foreground border-t border-border">
            No changes found for the selected filters.
          </div>
        ) : (
          changes.map((c, i) => (
            <div
              key={i}
              className="grid grid-cols-[1fr_auto_auto_auto_2fr] items-start gap-4 px-4 py-3 border-t border-border hover:bg-muted/30 transition-colors"
            >
              <div>
                <p className="text-sm font-medium truncate">{c.resource_name}</p>
                <p className="text-xs text-muted-foreground">{formatTime(c.timestamp)}</p>
              </div>
              <span className="text-xs text-muted-foreground">{c.resource_kind}</span>
              <span className="text-xs text-muted-foreground">{c.namespace || "—"}</span>
              <ChangeBadge type={c.change_type} />
              <p className="text-xs text-muted-foreground leading-relaxed">{c.change_summary || "—"}</p>
            </div>
          ))
        )}
      </div>

      {!loading && !error && changes.length > 0 && (
        <p className="text-xs text-muted-foreground text-right">
          Showing {changes.length} change{changes.length !== 1 ? "s" : ""}
        </p>
      )}
    </div>
  )
}
