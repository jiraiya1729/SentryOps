import { Suspense } from "react"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { getClusterSummary } from "@/lib/api/cluster"
import { ChatPanel } from "@/components/chat/chat-panel"
import { Toaster } from "sonner"

async function HeaderWithStatus() {
  const summary = await getClusterSummary().catch(() => null)
  return <Header databaseConnected={summary?.database_connected ?? false} />
}

export default function ClusterLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Suspense fallback={<Header databaseConnected={false} />}>
          <HeaderWithStatus />
        </Suspense>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
      <ChatPanel />
      <Toaster
        theme="light"
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast: "bg-card border border-border text-foreground shadow-sm",
            description: "text-muted-foreground",
          },
        }}
      />
    </div>
  )
}
