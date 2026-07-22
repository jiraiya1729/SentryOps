import { getNamespaces } from "@/lib/api/namespaces"
import { NamespacesTable } from "@/components/dashboard/namespaces-table"

export default async function NamespacesPage() {
  const namespaces = await getNamespaces()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Namespaces</h1>
        <p className="text-sm text-muted-foreground">
          Cluster namespaces and pod distribution
        </p>
      </div>
      <NamespacesTable data={namespaces.items} />
    </div>
  )
}
