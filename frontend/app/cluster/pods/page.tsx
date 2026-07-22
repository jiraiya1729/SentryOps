import { getPods } from "@/lib/api/pods"
import { PodsTable } from "@/components/dashboard/pods-table"

export default async function PodsPage() {
  const pods = await getPods()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Pods</h1>
        <p className="text-sm text-muted-foreground">
          All pods across namespaces
        </p>
      </div>
      <PodsTable data={pods.items} />
    </div>
  )
}
