import { notFound } from "next/navigation"
import Link from "next/link"
import { ExternalLink, CheckCircle, XCircle, GitCommit, ArrowRight, AlertTriangle } from "lucide-react"
import { getDeploymentHistoryById } from "@/lib/api/deployments"
import type { VerificationStatus } from "@/lib/types/api"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

const STATUS_COLOR: Record<VerificationStatus, string> = {
  healthy: "bg-green-500/10 text-green-500 border-green-500/20",
  degraded: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  failed: "bg-red-500/10 text-red-500 border-red-500/20",
  rolled_back: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
}

const HEALTH_COLOR = (score: number) =>
  score >= 90 ? "bg-green-500" : score >= 70 ? "bg-yellow-500" : "bg-red-500"

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold mb-4">{title}</h2>
      {children}
    </Card>
  )
}

export default async function DeploymentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  let data
  try {
    data = await getDeploymentHistoryById(id)
  } catch {
    notFound()
  }

  const { deployment: d, verification_checks: checks, impact_metrics: impact } = data
  const statusClass = STATUS_COLOR[d.verification_status] ?? STATUS_COLOR.pending
  const shortSha = d.git_sha ? d.git_sha.slice(0, 7) : ""

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/cluster/deployments" className="hover:text-foreground transition-colors">
          Deployments
        </Link>
        <span>/</span>
        <span className="text-foreground">{d.deployment_name}</span>
      </div>

      {/* Overview */}
      <Section title="Overview">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Deployment</span>
              <span className="text-sm font-medium">{d.namespace}/{d.deployment_name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Time</span>
              <span className="text-sm">{new Date(d.timestamp).toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Status</span>
              <Badge variant="outline" className={`text-xs ${statusClass}`}>
                {d.verification_status}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Health Score</span>
              <div className="flex items-center gap-2">
                <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full ${HEALTH_COLOR(d.health_score)}`}
                    style={{ width: `${d.health_score}%` }}
                  />
                </div>
                <span className="text-sm tabular-nums">{d.health_score.toFixed(0)}/100</span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <GitCommit className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{shortSha}</span>
                  <span className="text-sm text-muted-foreground truncate">{d.commit_author}</span>
                </div>
                <p className="text-sm mt-1 text-muted-foreground truncate">{d.commit_message || "No commit message"}</p>
              </div>
            </div>
            {d.pr_number > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Pull Request</span>
                {d.pr_url ? (
                  <a
                    href={d.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-blue-400 hover:underline"
                  >
                    #{d.pr_number} {d.pr_title?.slice(0, 40)}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                ) : (
                  <span className="text-sm">#{d.pr_number}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Image changes */}
        {(d.old_images.length > 0 || d.new_images.length > 0) && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground mb-2">Image changes</p>
            <div className="space-y-1">
              {d.new_images.map((img, i) => (
                <div key={i} className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-muted-foreground truncate max-w-[200px]">{d.old_images[i] || "—"}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  <span className="text-green-400 truncate max-w-[200px]">{img}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>

      {/* Verification Checks */}
      {checks.length > 0 && (
        <Section title="Verification Checks">
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 text-muted-foreground text-xs">
                  <th className="px-4 py-2 text-left font-medium">Check</th>
                  <th className="px-4 py-2 text-left font-medium">Status</th>
                  <th className="px-4 py-2 text-left font-medium">Value</th>
                  <th className="px-4 py-2 text-left font-medium">Threshold</th>
                  <th className="px-4 py-2 text-left font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((c, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-4 py-2.5 font-medium capitalize">{c.name.replace("_", " ")}</td>
                    <td className="px-4 py-2.5">
                      {c.passed ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-xs text-muted-foreground">{c.value?.toFixed(2)}</td>
                    <td className="px-4 py-2.5 tabular-nums text-xs text-muted-foreground">{c.threshold?.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{c.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Impact Metrics */}
      {impact.length > 0 && (
        <Section title="Impact Metrics">
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 text-muted-foreground text-xs">
                  <th className="px-4 py-2 text-left font-medium">Metric</th>
                  <th className="px-4 py-2 text-right font-medium">Before avg</th>
                  <th className="px-4 py-2 text-right font-medium">After avg</th>
                  <th className="px-4 py-2 text-right font-medium">Change</th>
                  <th className="px-4 py-2 text-right font-medium">Impact</th>
                </tr>
              </thead>
              <tbody>
                {impact.map((m, i) => {
                  const change = m.percent_change
                  const changeColor = change > 0 ? "text-red-400" : change < 0 ? "text-green-400" : "text-muted-foreground"
                  return (
                    <tr key={i} className="border-t border-border">
                      <td className="px-4 py-2.5 font-medium">{m.metric}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-xs">{m.before.avg.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-xs">{m.after.avg.toFixed(2)}</td>
                      <td className={`px-4 py-2.5 text-right tabular-nums text-xs ${changeColor}`}>
                        {change > 0 ? "+" : ""}{(change * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-xs">{m.impact_score.toFixed(1)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Files Changed */}
      {d.files_changed.length > 0 && (
        <Section title={`Files Changed (${d.files_changed.length})`}>
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            <span className="text-green-400">+{d.additions} additions</span>
            <span className="text-red-400">-{d.deletions} deletions</span>
          </div>
          <ul className="space-y-1">
            {d.files_changed.map((f, i) => (
              <li key={i} className="font-mono text-xs text-muted-foreground bg-muted/40 px-3 py-1.5 rounded">
                {f}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Linked Incidents */}
      {d.incident_ids.length > 0 && (
        <Section title="Linked Incidents">
          <ul className="space-y-2">
            {d.incident_ids.map((id) => (
              <li key={id}>
                <Link
                  href={`/cluster/guardian?investigation=${id}`}
                  className="flex items-center gap-2 text-sm text-blue-400 hover:underline"
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Investigation {id.slice(0, 8)}
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
