"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { toast } from "sonner"
import {
  getApprovals,
  approveInvestigation,
  rejectInvestigation,
} from "@/lib/api/guardian"
import type { ApprovalNotification } from "@/lib/types/api"

export function useGuardianApprovals() {
  const [approvals, setApprovals] = useState<ApprovalNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [includeResolved, setIncludeResolved] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const prevIdsRef = useRef<Set<string>>(new Set())
  const initialLoadRef = useRef(true)

  const fetchApprovals = useCallback(async () => {
    try {
      const data = await getApprovals(includeResolved)
      const currentPendingIds = new Set(
        data.approvals
          .filter((a) => !a.resolved)
          .map((a) => a.investigation_id)
      )

      if (!initialLoadRef.current) {
        for (const id of currentPendingIds) {
          if (!prevIdsRef.current.has(id)) {
            const newApproval = data.approvals.find(
              (a) => a.investigation_id === id
            )
            if (newApproval) {
              toast.warning("New approval required", {
                description: newApproval.summary,
                duration: 8000,
              })
            }
          }
        }
      }

      initialLoadRef.current = false
      prevIdsRef.current = currentPendingIds
      setApprovals(data.approvals)
    } catch {
      // silently ignore polling failures
    } finally {
      setLoading(false)
    }
  }, [includeResolved])

  useEffect(() => {
    fetchApprovals()
    const interval = setInterval(fetchApprovals, 10_000)
    return () => clearInterval(interval)
  }, [fetchApprovals])

  const approve = useCallback(
    async (investigationId: string, comment?: string) => {
      setActionLoading(investigationId)
      try {
        await approveInvestigation(investigationId, comment)
        toast.success("Remediation approved")
        await fetchApprovals()
      } catch (err) {
        toast.error("Failed to approve", {
          description:
            err instanceof Error ? err.message : "Unknown error",
        })
      } finally {
        setActionLoading(null)
      }
    },
    [fetchApprovals]
  )

  const reject = useCallback(
    async (investigationId: string, comment?: string) => {
      setActionLoading(investigationId)
      try {
        await rejectInvestigation(investigationId, comment)
        toast.success("Remediation rejected")
        await fetchApprovals()
      } catch (err) {
        toast.error("Failed to reject", {
          description:
            err instanceof Error ? err.message : "Unknown error",
        })
      } finally {
        setActionLoading(null)
      }
    },
    [fetchApprovals]
  )

  return {
    approvals,
    loading,
    includeResolved,
    setIncludeResolved,
    actionLoading,
    approve,
    reject,
    refresh: fetchApprovals,
  }
}
