import { getDeployments } from "@/lib/api/deployments"
import { DeploymentsTable } from "@/components/dashboard/deployments-table"

export default async function DeploymentsPage() {
  const deployments = await getDeployments()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Deployments</h1>
        <p className="text-sm text-muted-foreground">
          All deployments across namespaces
        </p>
      </div>
      <DeploymentsTable data={deployments.items} />
    </div>
  )
}
