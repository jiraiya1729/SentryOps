"use client"

import { Clock, Sparkles, X, AlertCircle, AlertTriangle, Info } from "lucide-react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { AlertSuggestion } from "@/lib/types/api"

const SEVERITY_CONFIG = {
  critical: {
    icon: AlertCircle,
    iconClass: "text-red-600",
    badge: "bg-red-50 text-red-700 border border-red-200",
  },
  high: {
    icon: AlertTriangle,
    iconClass: "text-orange-600",
    badge: "bg-orange-50 text-orange-700 border border-orange-200",
  },
  medium: {
    icon: AlertTriangle,
    iconClass: "text-amber-600",
    badge: "bg-amber-50 text-amber-700 border border-amber-200",
  },
  low: {
    icon: Info,
    iconClass: "text-violet-500",
    badge: "bg-violet-50 text-violet-700 border border-violet-200",
  },
  info: {
    icon: Info,
    iconClass: "text-stone-500",
    badge: "bg-stone-100 text-stone-600 border border-stone-200",
  },
} as const

function humanizeConditionType(conditionType: string): string {
  return conditionType
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

function TimeAgo({ iso }: { iso: string }) {
  const [label, setLabel] = useState("")

  useEffect(() => {
    function compute() {
      const diff = Date.now() - new Date(iso).getTime()
      const m = Math.floor(diff / 60_000)
      if (m < 60) return `${m}m ago`
      const h = Math.floor(m / 60)
      if (h < 24) return `${h}h ${m % 60}m ago`
      return `${Math.floor(h / 24)}d ${h % 24}h ago`
    }
    setLabel(compute())
    const interval = setInterval(() => setLabel(compute()), 60_000)
    return () => clearInterval(interval)
  }, [iso])

  return <span>{label}</span>
}

interface SuggestionCardProps {
  suggestion: AlertSuggestion
  onAccept: () => void
  onDismiss: () => void
  actionLoading: boolean
}

export function SuggestionCard({
  suggestion,
  onAccept,
  onDismiss,
  actionLoading,
}: SuggestionCardProps) {
  const cfg = SEVERITY_CONFIG[suggestion.severity]
  const Icon = cfg.icon

  return (
    <div
      className={cn(
        "rounded-xl border border-border/50 border-l-4 border-l-violet-500 p-4",
        "bg-card shadow-sm"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", cfg.iconClass)} />
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase bg-violet-50 text-violet-700 border border-violet-200">
                <Sparkles className="h-2.5 w-2.5" />
                AI Suggested
              </span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                  cfg.badge
                )}
              >
                {suggestion.severity}
              </span>
            </div>
            <p className="text-sm font-medium text-foreground">{suggestion.name}</p>
            {suggestion.description && (
              <p className="text-xs text-muted-foreground">{suggestion.description}</p>
            )}
            <p className="text-xs text-muted-foreground/70">
              Condition: {humanizeConditionType(suggestion.condition_type)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <Clock className="h-3 w-3" />
          <TimeAgo iso={suggestion.created_at} />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 pl-7">
        <Button
          size="sm"
          className="bg-green-600 hover:bg-green-700 text-white border-0"
          onClick={onAccept}
          disabled={actionLoading}
        >
          Accept
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          disabled={actionLoading}
        >
          <X className="h-3 w-3 mr-1" />
          Dismiss
        </Button>
      </div>
    </div>
  )
}
