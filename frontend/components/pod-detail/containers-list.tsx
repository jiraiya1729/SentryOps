import type { Container } from "@/lib/types/api"
import { ContainerCard } from "./container-card"

interface ContainersListProps {
  containers: Container[]
}

export function ContainersList({ containers }: ContainersListProps) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">
        Containers ({containers.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {containers.map((container) => (
          <ContainerCard key={container.name} container={container} />
        ))}
      </div>
    </div>
  )
}
