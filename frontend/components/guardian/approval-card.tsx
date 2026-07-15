"use client"

import { useState, useEffect } from "react"
import { Clock, AlertCircle, AlertTriangle, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { ApprovalNotification, RiskLevel } from "@/lib/types/api"

const SEVERITY_CONFIG = {
  critical: {
    border: "border-l-red-500",
    icon: AlertCircle,
    iconClass: "text-red-500",
    badge: "bg-red-500/20 text-red-400",
  },
  high: {
    border: "border-l-orange-500",
    icon: AlertTriangle,
    iconClass: "text-orange-500",
    badge: "bg-orange-500/20 text-orange-400",
  },
  medium: {
    border: "border-l-amber-500",
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    badge: "bg-amber-500/20 text-amber-400",
  },
  low: {
    border: "border-l-blue-500",
    icon: Info,
    iconClass: "text-blue-400",
    badge: "bg-blue-500/20 text-blue-400",
  },
  info: {
    border: "border-l-zinc-500",
    icon: Info,
    iconClass: "text-zinc-400",
    badge: "bg-zinc-500/20 text-zinc-400",
  },
} as const

const RISK_COLORS: Record<RiskLevel, string> = {
  low: "text-green-400 bg-green-500/10",
  medium: "text-amber-400 bg-amber-500/10",
  high: "text-red-400 bg-red-500/10",
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

interface ApprovalCardProps {
  approval: ApprovalNotification
  onApprove: () => void
  onReject: () => void
  actionLoading: boolean
}

export function ApprovalCard({
  approval,
  onApprove,
  onReject,
  actionLoading,
}: ApprovalCardProps) {
  const cfg = SEVERITY_CONFIG[approval.severity]
  const Icon = cfg.icon

  return (
    <div
      className={cn(
        "rounded-xl border border-border/50 border-l-4 p-4",
        "bg-card/50 backdrop-blur-md",
        cfg.border
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", cfg.iconClass)} />
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                  cfg.badge
                )}
              >
                {approval.severity}
              </span>
              {(approval.namespace || approval.resource) && (
                <span className="text-[10px] font-mono text-muted-foreground">
                  {approval.namespace}
                  {approval.resource ? `/${approval.resource}` : ""}
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-foreground">
              {approval.summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <Clock className="h-3 w-3" />
          <TimeAgo iso={approval.created_at} />
        </div>
      </div>

      {approval.remediations.length > 0 && (
        <div className="mt-3 space-y-1.5 pl-7">
          {approval.remediations
            .filter((r) => r.requires_approval)
            .map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 font-medium",
                    RISK_COLORS[r.risk_level]
                  )}
                >
                  {r.risk_level}
                </span>
                <span className="text-muted-foreground">{r.action}</span>
                <span className="font-mono text-[10px] text-muted-foreground/60">
                  ({r.type})
                </span>
              </div>
            ))}
        </div>
      )}

      {!approval.resolved && (
        <div className="mt-4 flex items-center gap-2 pl-7">
          <Button size="sm" onClick={onApprove} disabled={actionLoading}>
            Approve
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={onReject}
            disabled={actionLoading}
          >
            Reject
          </Button>
        </div>
      )}

      {approval.resolved && (
        <div className="mt-3 pl-7 text-xs text-muted-foreground">
          {approval.resolution === "approved" ? "Approved" : "Rejected"}
          {approval.resolved_at &&
            ` • ${new Date(approval.resolved_at).toLocaleString()}`}
        </div>
      )}
    </div>
  )
}
