import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface SummaryCardProps {
  label: string
  value: number
  icon: LucideIcon
  variant?: "default" | "success" | "warning" | "danger"
}

const variantBorder = {
  default: "border-l-primary",
  success: "border-l-success",
  warning: "border-l-warning",
  danger: "border-l-destructive",
}

export function SummaryCard({ label, value, icon: Icon, variant = "default" }: SummaryCardProps) {
  return (
    <div className={cn("bg-card rounded-lg shadow-sm p-4 border-l-3", variantBorder[variant])}>
      <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
        <Icon className="h-3.5 w-3.5" />
        <p className="text-xs font-medium">{label}</p>
      </div>
      <p className="text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
    </div>
  )
}
