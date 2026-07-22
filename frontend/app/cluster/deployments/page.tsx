"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { ExternalLink, CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react"
import { getDeploymentHistory } from "@/lib/api/deployments"
import type { DeploymentEvent, VerificationStatus } from "@/lib/types/api"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

const STATUS_CONFIG: Record<VerificationStatus, { label: string; icon: React.ReactNode; className: string }> = {
  healthy: { label: "Healthy", icon: <CheckCircle className="h-3 w-3" />, className: "bg-green-50 text-green-700 border-green-200" },
  degraded: { label: "Degraded", icon: <AlertTriangle className="h-3 w-3" />, className: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  failed: { label: "Failed", icon: <XCircle className="h-3 w-3" />, className: "bg-red-50 text-red-700 border-red-200" },
  rolled_back: { label: "Rolled Back", icon: <XCircle className="h-3 w-3" />, className: "bg-orange-50 text-orange-700 border-orange-200" },
  pending: { label: "Pending", icon: <Clock className="h-3 w-3" />, className: "bg-stone-50 text-stone-600 border-stone-200" },
}

function HealthBar({ score }: { score: number }) {
  const color = score >= 90 ? "bg-green-500" : score >= 70 ? "bg-yellow-500" : "bg-red-500"
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">{score.toFixed(0)}</span>
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="bg-muted/50 h-9" />
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3 border-t border-border">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  )
}

export default function DeploymentsPage() {
  const router = useRouter()
  const [deployments, setDeployments] = useState<DeploymentEvent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [namespace, setNamespace] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [hours, setHours] = useState(24)

  const fetchDeployments = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getDeploymentHistory({
        namespace: namespace || undefined,
        status: statusFilter || undefined,
        hours,
        limit: 50,
      })
      setDeployments(data.deployments)
      setTotal(data.total)
    } catch {
      setDeployments([])
    } finally {
      setLoading(false)
    }
  }, [namespace, statusFilter, hours])

  useEffect(() => {
    fetchDeployments()
  }, [fetchDeployments])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Deployment History</h1>
        <p className="text-sm text-muted-foreground">
          Track deployment events, health scores, and git context
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Namespace"
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-40"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">All statuses</option>
          <option value="healthy">Healthy</option>
          <option value="degraded">Degraded</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
        </select>
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="h-8 rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value={6}>Last 6h</option>
          <option value={24}>Last 24h</option>
          <option value={48}>Last 48h</option>
          <option value={168}>Last 7d</option>
        </select>
        <span className="text-xs text-muted-foreground ml-auto">{total} total</span>
      </div>

      {/* Table */}
      {loading ? (
        <TableSkeleton />
      ) : deployments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-2">
          <Clock className="h-8 w-8 opacity-30" />
          <p className="text-sm">No deployments found</p>
          <p className="text-xs opacity-60">Deployments will appear here once detected</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-muted-foreground text-xs">
                <th className="px-4 py-2.5 text-left font-medium">Time</th>
                <th className="px-4 py-2.5 text-left font-medium">Namespace / Deployment</th>
                <th className="px-4 py-2.5 text-left font-medium">Author</th>
                <th className="px-4 py-2.5 text-left font-medium">Commit</th>
                <th className="px-4 py-2.5 text-left font-medium">Health</th>
                <th className="px-4 py-2.5 text-left font-medium">Status</th>
                <th className="px-4 py-2.5 text-left font-medium">PR</th>
              </tr>
            </thead>
            <tbody>
              {deployments.map((d) => {
                const st = STATUS_CONFIG[d.verification_status] ?? STATUS_CONFIG.pending
                const shortSha = d.git_sha ? d.git_sha.slice(0, 7) : ""
                const ts = new Date(d.timestamp).toLocaleString()
                return (
                  <tr
                    key={d.id}
                    className="border-t border-border hover:bg-muted/40 cursor-pointer transition-colors"
                    onClick={() => router.push(`/cluster/deployments/${d.id}`)}
                  >
                    <td className="px-4 py-2.5 text-muted-foreground text-xs whitespace-nowrap">{ts}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-muted-foreground text-xs">{d.namespace}/</span>
                      <span className="font-medium">{d.deployment_name}</span>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground text-xs">{d.commit_author || "—"}</td>
                    <td className="px-4 py-2.5 max-w-[200px]">
                      {shortSha && (
                        <span className="font-mono text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded mr-2">{shortSha}</span>
                      )}
                      <span className="text-xs truncate">{d.commit_message?.slice(0, 60) || "—"}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <HealthBar score={d.health_score} />
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline" className={`flex items-center gap-1 w-fit text-xs ${st.className}`}>
                        {st.icon}
                        {st.label}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">
                      {d.pr_url && d.pr_number > 0 ? (
                        <a
                          href={d.pr_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          #{d.pr_number}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
