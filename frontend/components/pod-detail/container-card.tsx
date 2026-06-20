import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "@/components/shared/status-badge"
import { Package, RotateCcw } from "lucide-react"
import type { Container } from "@/lib/types/api"

interface ContainerCardProps {
  container: Container
}

export function ContainerCard({ container }: ContainerCardProps) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">{container.name}</span>
          </div>
          <StatusBadge status={container.state} />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Image:</span>
            <span className="font-mono text-muted-foreground truncate">
              {container.image}
            </span>
          </div>

          {container.reason && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Reason:</span>
              <span className="text-destructive">{container.reason}</span>
            </div>
          )}

          <div className="flex items-center gap-1.5 text-xs">
            <RotateCcw className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Restarts:</span>
            <span
              className={
                container.restart_count > 5
                  ? "text-destructive font-medium"
                  : ""
              }
            >
              {container.restart_count}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
