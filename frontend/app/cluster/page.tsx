import { Suspense } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SummaryCards } from "@/components/dashboard/summary-cards"
import { PodsTable } from "@/components/dashboard/pods-table"
import { DeploymentsTable } from "@/components/dashboard/deployments-table"
import { getPods } from "@/lib/api/pods"
import { getDeployments } from "@/lib/api/deployments"
import { Skeleton } from "@/components/ui/skeleton"

function SummaryCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-[88px] rounded-lg" />
      ))}
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-8 w-20" />
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 h-9" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-3 border-t border-border">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-5 w-16 rounded-md" />
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-8" />
            <Skeleton className="h-4 w-32" />
          </div>
        ))}
      </div>
    </div>
  )
}

async function PodsSection() {
  const pods = await getPods()
  return <PodsTable data={pods.items} />
}

async function DeploymentsSection() {
  const deployments = await getDeployments()
  return <DeploymentsTable data={deployments.items} />
}

export default function ClusterPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Cluster Overview</h1>
        <p className="text-sm text-muted-foreground">
          Monitor your Kubernetes cluster resources
        </p>
      </div>

      <Suspense fallback={<SummaryCardsSkeleton />}>
        <SummaryCards />
      </Suspense>

      <Tabs defaultValue="pods" className="space-y-4">
        <TabsList className="bg-muted border border-border">
          <TabsTrigger value="pods">Pods</TabsTrigger>
          <TabsTrigger value="deployments">Deployments</TabsTrigger>
        </TabsList>

        <TabsContent value="pods">
          <Suspense fallback={<TableSkeleton />}>
            <PodsSection />
          </Suspense>
        </TabsContent>

        <TabsContent value="deployments">
          <Suspense fallback={<TableSkeleton />}>
            <DeploymentsSection />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  )
}
