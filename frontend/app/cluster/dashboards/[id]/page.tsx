"use client"

import { use, useState, useEffect, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Plus, Edit2 } from "lucide-react"
import { getDashboard, removePanel } from "@/lib/api/dashboards"
import { PanelRenderer } from "@/components/dashboards/panel-renderer"
import { PanelBuilder } from "@/components/dashboards/panel-builder"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import type { Dashboard, DashboardPanel } from "@/lib/types/api"

const TIME_RANGES = ["5m", "15m", "1h", "6h", "24h"]

export default function DashboardDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const router = useRouter()
  const [dashboard, setDashboard] = useState<(Dashboard & { panels: DashboardPanel[] }) | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState("1h")
  const [editMode, setEditMode] = useState(false)
  const [addPanelOpen, setAddPanelOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await getDashboard(id)
      setDashboard(data)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchDashboard()
  }, [fetchDashboard, refreshKey])

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setRefreshKey((k) => k + 1)
    }, 30_000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  async function handleRemovePanel(panelId: string) {
    await removePanel(id, panelId)
    setRefreshKey((k) => k + 1)
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-6 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-64 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/cluster/dashboards")}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <p className="text-sm text-muted-foreground">Dashboard not found.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        size="sm"
        className="text-muted-foreground -ml-1"
        onClick={() => router.push("/cluster/dashboards")}
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Dashboards
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">{dashboard.name}</h1>
          {dashboard.description && (
            <p className="text-sm text-muted-foreground">{dashboard.description}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5">
            {TIME_RANGES.map((tr) => (
              <button
                key={tr}
                onClick={() => setTimeRange(tr)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  timeRange === tr
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tr}
              </button>
            ))}
          </div>
          <Button
            variant={editMode ? "default" : "outline"}
            size="sm"
            onClick={() => setEditMode((v) => !v)}
          >
            <Edit2 className="h-3.5 w-3.5 mr-1" />
            {editMode ? "Done" : "Edit"}
          </Button>
          <Button size="sm" onClick={() => setAddPanelOpen(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add Panel
          </Button>
        </div>
      </div>

      {dashboard.panels.length === 0 ? (
        <EmptyState
          title="No panels yet"
          message="Click Add Panel to start building your dashboard"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {dashboard.panels.map((panel) => (
            <PanelRenderer
              key={`${panel.id}-${refreshKey}`}
              panel={panel}
              timeRange={timeRange}
              editMode={editMode}
              onRemove={() => handleRemovePanel(panel.id)}
            />
          ))}
        </div>
      )}

      <PanelBuilder
        open={addPanelOpen}
        onOpenChange={setAddPanelOpen}
        dashboardId={id}
        onPanelAdded={() => {
          setRefreshKey((k) => k + 1)
          setAddPanelOpen(false)
        }}
      />
    </div>
  )
}
