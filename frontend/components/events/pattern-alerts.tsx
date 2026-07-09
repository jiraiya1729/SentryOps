"use client"

import { useState } from "react"
import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DetectedPattern } from "@/lib/types/api"

const SEVERITY_CONFIG = {
  critical: {
    border: "border-l-red-500",
    bg: "bg-red-500/5",
    icon: AlertCircle,
    iconClass: "text-red-500 animate-pulse",
    badge: "bg-red-500/20 text-red-400",
    label: "Critical",
  },
  warning: {
    border: "border-l-amber-500",
    bg: "bg-amber-500/5",
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    badge: "bg-amber-500/20 text-amber-400",
    label: "Warning",
  },
  info: {
    border: "border-l-blue-500",
    bg: "bg-blue-500/5",
    icon: Info,
    iconClass: "text-blue-400",
    badge: "bg-blue-500/20 text-blue-400",
    label: "Info",
  },
} as const

interface PatternAlertsProps {
  patterns: DetectedPattern[]
}

export function PatternAlerts({ patterns }: PatternAlertsProps) {
  const [expanded, setExpanded] = useState(false)

  if (patterns.length === 0) return null

  const sorted = [...patterns].sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 }
    return order[a.severity] - order[b.severity]
  })

  const visible = expanded ? sorted : sorted.slice(0, 3)
  const hiddenCount = sorted.length - 3

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Detected Patterns
        </h3>
        <span className="text-xs text-muted-foreground">
          {sorted.length} pattern{sorted.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-1.5">
        {visible.map((p, i) => {
          const cfg = SEVERITY_CONFIG[p.severity]
          const Icon = cfg.icon
          return (
            <div
              key={`${p.namespace}/${p.kind}/${p.name}/${i}`}
              className={cn(
                "border-l-2 rounded-r-md px-4 py-3",
                "backdrop-blur-sm border border-border/50",
                cfg.border,
                cfg.bg
              )}
            >
              <div className="flex items-start gap-3">
                <Icon className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", cfg.iconClass)} />
                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={cn(
                        "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                        cfg.badge
                      )}
                    >
                      {cfg.label}
                    </span>
                    <span className="text-xs font-medium text-foreground">{p.pattern}</span>
                    <span className="ml-auto text-[10px] font-mono text-muted-foreground">
                      {p.namespace}/{p.kind}/{p.name}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{p.description}</p>
                  {p.event_count > 0 && (
                    <span className="text-[10px] text-muted-foreground">
                      {p.event_count} matching event{p.event_count !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {sorted.length > 3 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              Show fewer
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              {hiddenCount} more pattern{hiddenCount !== 1 ? "s" : ""}
            </>
          )}
        </button>
      )}
    </div>
  )
}
