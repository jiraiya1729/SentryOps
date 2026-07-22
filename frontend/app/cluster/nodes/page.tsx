import { getNodes } from "@/lib/api/nodes"
import { NodesTable } from "@/components/dashboard/nodes-table"

export default async function NodesPage() {
  const nodes = await getNodes()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Nodes</h1>
        <p className="text-sm text-muted-foreground">
          Cluster nodes and their status
        </p>
      </div>
      <NodesTable data={nodes.items} />
    </div>
  )
}
