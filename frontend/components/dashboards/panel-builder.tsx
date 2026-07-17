"use client"

import { useState, useEffect } from "react"
import { BarChart3, Hash, FileText, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { addPanel } from "@/lib/api/dashboards"
import type { DashboardPanel } from "@/lib/types/api"

interface PanelBuilderProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  dashboardId: string
  onPanelAdded: () => void
}

type PanelType = DashboardPanel["panel_type"]

const PANEL_TYPES: { type: PanelType; label: string; description: string; icon: React.ReactNode }[] = [
  { type: "metric_chart", label: "Metric Chart", description: "Time-series line chart", icon: <BarChart3 className="h-6 w-6" /> },
  { type: "stat_card", label: "Stat Card", description: "Single aggregated value", icon: <Hash className="h-6 w-6" /> },
  { type: "log_table", label: "Log Table", description: "Recent log lines", icon: <FileText className="h-6 w-6" /> },
  { type: "event_list", label: "Event List", description: "Kubernetes events", icon: <Bell className="h-6 w-6" /> },
]

const METRICS = [
  { value: "cpu_usage_cores", label: "CPU Usage (cores)" },
  { value: "memory_usage_bytes", label: "Memory Usage (bytes)" },
  { value: "network_rx_bytes", label: "Network RX (bytes)" },
  { value: "network_tx_bytes", label: "Network TX (bytes)" },
]

const AGGREGATIONS = [
  { value: "avg", label: "Average" },
  { value: "max", label: "Maximum" },
  { value: "sum", label: "Sum" },
]

const GROUP_BY_OPTIONS = [
  { value: "pod_name", label: "Pod" },
  { value: "node_name", label: "Node" },
  { value: "namespace", label: "Namespace" },
]

const LOG_LEVELS = [
  { value: "", label: "All levels" },
  { value: "error", label: "Error" },
  { value: "warning", label: "Warning" },
  { value: "info", label: "Info" },
]

const EVENT_TYPES = [
  { value: "", label: "All types" },
  { value: "Warning", label: "Warning" },
  { value: "Normal", label: "Normal" },
]

const FORMAT_OPTIONS = [
  { value: "number", label: "Number" },
  { value: "bytes", label: "Bytes" },
  { value: "percent", label: "Percent" },
]

export function PanelBuilder({ open, onOpenChange, dashboardId, onPanelAdded }: PanelBuilderProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [panelType, setPanelType] = useState<PanelType | null>(null)
  const [queryConfig, setQueryConfig] = useState<Record<string, unknown>>({})
  const [displayConfig, setDisplayConfig] = useState<Record<string, unknown>>({})
  const [title, setTitle] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) {
      setStep(1)
      setPanelType(null)
      setQueryConfig({})
      setDisplayConfig({})
      setTitle("")
      setSubmitting(false)
    }
  }, [open])

  function setQC(key: string, value: unknown) {
    setQueryConfig((prev) => ({ ...prev, [key]: value }))
  }

  function setDC(key: string, value: unknown) {
    setDisplayConfig((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    if (!panelType || !title.trim()) return
    setSubmitting(true)
    try {
      await addPanel(dashboardId, {
        title: title.trim(),
        panel_type: panelType,
        query_config: queryConfig,
        display_config: displayConfig,
      })
      onPanelAdded()
      onOpenChange(false)
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogTitle>Add Panel — Step {step} of 3</DialogTitle>

        {step === 1 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Choose a panel type</p>
            <div className="grid grid-cols-2 gap-3">
              {PANEL_TYPES.map((pt) => (
                <button
                  key={pt.type}
                  onClick={() => { setPanelType(pt.type); setStep(2) }}
                  className={`flex flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors hover:bg-accent ${
                    panelType === pt.type ? "border-primary bg-accent" : "border-border"
                  }`}
                >
                  {pt.icon}
                  <span className="font-medium">{pt.label}</span>
                  <span className="text-xs text-muted-foreground text-center">{pt.description}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && panelType && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Configure query</p>
            <QueryBuilder panelType={panelType} queryConfig={queryConfig} setQC={setQC} />
            <div className="flex justify-between pt-2">
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>Back</Button>
              <Button size="sm" onClick={() => setStep(3)}>Next</Button>
            </div>
          </div>
        )}

        {step === 3 && panelType && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Display options</p>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Panel title *</label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. CPU Usage by Pod"
                  className="h-8 text-sm"
                />
              </div>
              {panelType === "metric_chart" && (
                <>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Chart type</label>
                    <div className="flex gap-2">
                      {["line", "area"].map((ct) => (
                        <button
                          key={ct}
                          onClick={() => setDC("chart_type", ct)}
                          className={`rounded-md border px-3 py-1 text-xs capitalize transition-colors ${
                            (displayConfig.chart_type ?? "line") === ct
                              ? "border-primary bg-accent"
                              : "border-border hover:bg-accent"
                          }`}
                        >
                          {ct}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="show-legend"
                      checked={!!displayConfig.show_legend}
                      onChange={(e) => setDC("show_legend", e.target.checked)}
                      className="h-3.5 w-3.5"
                    />
                    <label htmlFor="show-legend" className="text-xs">Show legend</label>
                  </div>
                </>
              )}
              {panelType === "stat_card" && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Format</label>
                  <Select
                    value={String(queryConfig.format ?? "number")}
                    onChange={(v) => setQC("format", v)}
                    options={FORMAT_OPTIONS}
                  />
                </div>
              )}
            </div>
            <div className="flex justify-between pt-2">
              <Button variant="ghost" size="sm" onClick={() => setStep(2)}>Back</Button>
              <Button size="sm" onClick={handleSubmit} disabled={!title.trim() || submitting}>
                {submitting ? "Adding…" : "Add Panel"}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function QueryBuilder({
  panelType,
  queryConfig,
  setQC,
}: {
  panelType: PanelType
  queryConfig: Record<string, unknown>
  setQC: (k: string, v: unknown) => void
}) {
  if (panelType === "metric_chart") {
    return (
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Metric</label>
          <Select
            value={String(queryConfig.metric ?? "cpu_usage_cores")}
            onChange={(v) => setQC("metric", v)}
            options={METRICS}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Aggregation</label>
          <Select
            value={String(queryConfig.aggregation ?? "avg")}
            onChange={(v) => setQC("aggregation", v)}
            options={AGGREGATIONS}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Group by</label>
          <Select
            value={String(queryConfig.group_by ?? "pod_name")}
            onChange={(v) => setQC("group_by", v)}
            options={GROUP_BY_OPTIONS}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Namespace (optional)</label>
          <Input
            value={String(queryConfig.namespace ?? "")}
            onChange={(e) => setQC("namespace", e.target.value || undefined)}
            placeholder="default"
            className="h-8 text-sm"
          />
        </div>
      </div>
    )
  }

  if (panelType === "stat_card") {
    return (
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Metric</label>
          <Select
            value={String(queryConfig.metric ?? "cpu_usage_cores")}
            onChange={(v) => setQC("metric", v)}
            options={METRICS}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Aggregation</label>
          <Select
            value={String(queryConfig.aggregation ?? "avg")}
            onChange={(v) => setQC("aggregation", v)}
            options={AGGREGATIONS}
          />
        </div>
      </div>
    )
  }

  if (panelType === "log_table") {
    return (
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Log level</label>
          <Select
            value={String(queryConfig.level ?? "")}
            onChange={(v) => setQC("level", v || undefined)}
            options={LOG_LEVELS}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Namespace (optional)</label>
          <Input
            value={String(queryConfig.namespace ?? "")}
            onChange={(e) => setQC("namespace", e.target.value || undefined)}
            placeholder="default"
            className="h-8 text-sm"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Search (optional)</label>
          <Input
            value={String(queryConfig.query ?? "")}
            onChange={(e) => setQC("query", e.target.value || undefined)}
            placeholder="error message…"
            className="h-8 text-sm"
          />
        </div>
      </div>
    )
  }

  if (panelType === "event_list") {
    return (
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Event type</label>
          <Select
            value={String(queryConfig.event_type ?? "")}
            onChange={(v) => setQC("event_type", v || undefined)}
            options={EVENT_TYPES}
          />
        </div>
      </div>
    )
  }

  return null
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}
