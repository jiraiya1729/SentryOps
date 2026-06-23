import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { getClusterSummary } from "@/lib/api/cluster"

export default async function ClusterLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const summary = await getClusterSummary().catch(() => null)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header databaseConnected={summary?.database_connected ?? false} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
