"use client"

import { Clock, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Namespace } from "@/lib/types/api"

const TIME_RANGES = [
  { label: "1h", value: "1h" },
  { label: "6h", value: "6h" },
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
]

interface MetricsFiltersProps {
  timeRange: string
  onTimeRangeChange: (value: string) => void
  namespace: string
  onNamespaceChange: (value: string) => void
  namespaces: Namespace[]
  lastUpdated: Date | null
}

export function MetricsFilters({
  timeRange,
  onTimeRangeChange,
  namespace,
  onNamespaceChange,
  namespaces,
  lastUpdated,
}: MetricsFiltersProps) {
  const timeSince = lastUpdated
    ? Math.round((Date.now() - lastUpdated.getTime()) / 1000)
    : null

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
        {TIME_RANGES.map((range) => (
          <Button
            key={range.value}
            variant={timeRange === range.value ? "default" : "ghost"}
            size="xs"
            onClick={() => onTimeRangeChange(range.value)}
          >
            {range.label}
          </Button>
        ))}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 h-8 text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors">
          <Clock className="h-3.5 w-3.5" />
          {namespace || "All Namespaces"}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={() => onNamespaceChange("")}>
            All Namespaces
          </DropdownMenuItem>
          {namespaces.map((ns) => (
            <DropdownMenuItem
              key={ns.name}
              onClick={() => onNamespaceChange(ns.name)}
            >
              {ns.name}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {timeSince !== null && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground ml-auto">
          <RefreshCw className="h-3 w-3 animate-spin" />
          <span>Updated {timeSince}s ago</span>
        </div>
      )}
    </div>
  )
}
