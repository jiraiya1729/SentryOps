"use client"

import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/shared/empty-state"
import { ApprovalCard } from "./approval-card"
import { ConfirmationDialog } from "./confirmation-dialog"
import { useGuardianApprovals } from "@/hooks/use-guardian-approvals"
import type { ApprovalNotification } from "@/lib/types/api"

export function ApprovalPanel() {
  const {
    approvals,
    loading,
    includeResolved,
    setIncludeResolved,
    actionLoading,
    approve,
    reject,
    refresh,
  } = useGuardianApprovals()

  const [dialogState, setDialogState] = useState<{
    open: boolean
    type: "approve" | "reject"
    approval: ApprovalNotification | null
  }>({ open: false, type: "approve", approval: null })

  const pending = approvals.filter((a) => !a.resolved)
  const resolved = approvals.filter((a) => a.resolved)

  const handleAction = (
    type: "approve" | "reject",
    approval: ApprovalNotification
  ) => {
    setDialogState({ open: true, type, approval })
  }

  const handleConfirm = (comment?: string) => {
    if (!dialogState.approval) return
    const fn = dialogState.type === "approve" ? approve : reject
    fn(dialogState.approval.investigation_id, comment)
    setDialogState({ open: false, type: "approve", approval: null })
  }

  if (loading) return <ApprovalPanelSkeleton />

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">
            Pending Approvals ({pending.length})
          </h2>
          <Button variant="ghost" size="icon-sm" onClick={refresh}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
        {pending.length === 0 ? (
          <EmptyState
            title="No pending approvals"
            message="All clear. No remediations require your approval."
          />
        ) : (
          <div className="space-y-3">
            {pending.map((a) => (
              <ApprovalCard
                key={a.investigation_id}
                approval={a}
                onApprove={() => handleAction("approve", a)}
                onReject={() => handleAction("reject", a)}
                actionLoading={actionLoading === a.investigation_id}
              />
            ))}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-muted-foreground">
            History
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIncludeResolved(!includeResolved)}
            className="text-xs"
          >
            {includeResolved ? "Hide resolved" : "Show resolved"}
          </Button>
        </div>
        {includeResolved && resolved.length > 0 && (
          <div className="space-y-3 opacity-60">
            {resolved.map((a) => (
              <ApprovalCard
                key={a.investigation_id}
                approval={a}
                onApprove={() => {}}
                onReject={() => {}}
                actionLoading={false}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={dialogState.open}
        onOpenChange={(open) => setDialogState((s) => ({ ...s, open }))}
        title={
          dialogState.type === "approve"
            ? "Approve Remediation"
            : "Reject Remediation"
        }
        description={
          dialogState.type === "approve"
            ? `This will execute the proposed remediation actions on ${dialogState.approval?.resource || "the target resource"}. Are you sure?`
            : "This will reject and close the investigation without executing any remediation. Are you sure?"
        }
        confirmLabel={dialogState.type === "approve" ? "Approve" : "Reject"}
        variant={dialogState.type === "reject" ? "destructive" : "default"}
        onConfirm={handleConfirm}
        loading={!!actionLoading}
      />
    </div>
  )
}

function ApprovalPanelSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-32 rounded-xl" />
      ))}
    </div>
  )
}
