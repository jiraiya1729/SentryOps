import { Box, Server, Network, CircleCheck, Clock, CircleX } from "lucide-react"
import { getClusterSummary } from "@/lib/api/cluster"
import { SummaryCard } from "./summary-card"

export async function SummaryCards() {
  const summary = await getClusterSummary()

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <SummaryCard
        label="Total Pods"
        value={summary.pods}
        icon={Box}
      />
      <SummaryCard
        label="Nodes"
        value={summary.nodes}
        icon={Server}
      />
      <SummaryCard
        label="Namespaces"
        value={summary.namespaces}
        icon={Network}
      />
      <SummaryCard
        label="Running"
        value={summary.running_pods}
        icon={CircleCheck}
        variant="success"
      />
      <SummaryCard
        label="Pending"
        value={summary.pending_pods}
        icon={Clock}
        variant="warning"
      />
      <SummaryCard
        label="Failed"
        value={summary.failed_pods}
        icon={CircleX}
        variant="danger"
      />
    </div>
  )
}
