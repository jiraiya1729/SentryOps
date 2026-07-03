import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { getPodDetail, getPodEvents } from "@/lib/api/pods"
import { PodMetadata } from "@/components/pod-detail/pod-metadata"
import { ContainersList } from "@/components/pod-detail/containers-list"
import { EventsTimeline } from "@/components/pod-detail/events-timeline"
import { PodMetricsSection } from "@/components/pod-detail/pod-metrics-section"
import { Button } from "@/components/ui/button"

export default async function PodDetailPage({
  params,
}: {
  params: Promise<{ namespace: string; name: string }>
}) {
  const { namespace, name } = await params

  const [pod, eventsData] = await Promise.all([
    getPodDetail(namespace, name),
    getPodEvents(namespace, name),
  ])

  const podStatus =
    pod.containers.find((c) => c.reason)?.reason ??
    pod.containers.find((c) => c.state !== "running")?.state ??
    "Running"

  return (
    <div className="space-y-6">
      <Link href="/cluster">
        <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground -ml-2">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Cluster
        </Button>
      </Link>

      <PodMetadata pod={pod} status={podStatus} />
      <ContainersList containers={pod.containers} />
      <EventsTimeline events={eventsData.events} />
      <PodMetricsSection namespace={namespace} name={name} />
    </div>
  )
}
