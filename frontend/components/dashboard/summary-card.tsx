import { Card, CardContent } from "@/components/ui/card"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface SummaryCardProps {
  label: string
  value: number
  icon: LucideIcon
  variant?: "default" | "success" | "warning" | "danger"
}

const variantStyles = {
  default: "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-destructive",
}

export function SummaryCard({ label, value, icon: Icon, variant = "default" }: SummaryCardProps) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className="text-2xl font-semibold tracking-tight">{value}</p>
          </div>
          <div
            className={cn(
              "flex items-center justify-center w-10 h-10 rounded-lg bg-muted",
              variantStyles[variant]
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
