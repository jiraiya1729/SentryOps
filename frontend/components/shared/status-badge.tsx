import { cn } from "@/lib/utils"

type StatusVariant = "success" | "warning" | "danger" | "orange" | "default"

function getVariant(status: string): StatusVariant {
  const lower = status.toLowerCase()

  if (
    ["running", "healthy", "active", "available", "ready", "succeeded"].includes(lower)
  ) {
    return "success"
  }

  if (["pending", "waiting", "containercreating"].includes(lower)) {
    return "warning"
  }

  if (
    [
      "failed",
      "crashloopbackoff",
      "error",
      "unavailable",
      "imagepullbackoff",
      "evicted",
      "oomkilled",
    ].includes(lower)
  ) {
    return "danger"
  }

  if (["degraded", "unknown", "terminating", "unhealthy"].includes(lower)) {
    return "orange"
  }

  return "default"
}

const variantStyles: Record<StatusVariant, string> = {
  success: "bg-success/10 text-success border-success/20",
  warning: "bg-warning/10 text-warning border-warning/20",
  danger: "bg-destructive/10 text-destructive border-destructive/20",
  orange: "bg-orange/10 text-orange border-orange/20",
  default: "bg-muted text-muted-foreground border-border",
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const variant = getVariant(status)

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", {
          "bg-success": variant === "success",
          "bg-warning": variant === "warning",
          "bg-destructive": variant === "danger",
          "bg-orange": variant === "orange",
          "bg-muted-foreground": variant === "default",
        })}
      />
      {status}
    </span>
  )
}
