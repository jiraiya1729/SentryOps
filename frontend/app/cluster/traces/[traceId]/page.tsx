import { getTrace } from "@/lib/api/traces"
import { TraceWaterfall } from "@/components/traces/trace-waterfall"
import { CorrelationPanel } from "@/components/traces/correlation-panel"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { formatDuration } from "@/lib/traces-utils"

interface Props {
  params: Promise<{ traceId: string }>
}

export default async function TraceDetailPage({ params }: Props) {
  const { traceId } = await params
  const trace = await getTrace(traceId)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/cluster/traces">
          <Button variant="ghost" size="sm" className="-ml-2 gap-1.5 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-3.5 w-3.5" />
            Traces
          </Button>
        </Link>
      </div>

      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-lg font-semibold tracking-tight">Trace Detail</h1>
        </div>
        <p className="mt-1 font-mono text-xs text-muted-foreground">{traceId}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-xs text-muted-foreground">Duration</p>
          <p className="mt-1 text-sm font-medium">
            {formatDuration(
              trace.spans.reduce((acc, s) => Math.max(acc, (new Date(s.timestamp).getTime() - new Date(trace.start_time ?? s.timestamp).getTime()) + s.duration_ms), 0)
            )}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-xs text-muted-foreground">Spans</p>
          <p className="mt-1 text-sm font-medium">{trace.span_count}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-xs text-muted-foreground">Services</p>
          <p className="mt-1 text-sm font-medium">{trace.services.length}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-xs text-muted-foreground">Errors</p>
          <p className="mt-1 text-sm font-medium text-destructive">
            {trace.spans.filter((s) => s.status_code === "ERROR").length}
          </p>
        </div>
      </div>

      <TraceWaterfall trace={trace} />

      <CorrelationPanel traceId={traceId} />
    </div>
  )
}
