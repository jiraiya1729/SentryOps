import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "@/components/shared/status-badge"
import { Server, Network, Globe, Activity } from "lucide-react"
import type { PodDetail } from "@/lib/types/api"

interface PodMetadataProps {
  pod: PodDetail
  status: string
}

export function PodMetadata({ pod, status }: PodMetadataProps) {
  const items = [
    { label: "Namespace", value: pod.namespace, icon: Network },
    { label: "Node", value: pod.node ?? "Unassigned", icon: Server },
    { label: "IP", value: pod.ip ?? "None", icon: Globe },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">{pod.name}</h1>
        <StatusBadge status={status} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((item) => (
          <Card key={item.label} className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-md bg-muted">
                  <item.icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="text-sm font-medium font-mono">{item.value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
