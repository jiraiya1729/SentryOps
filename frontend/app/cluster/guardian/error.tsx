"use client"

import { ErrorState } from "@/components/shared/error-state"

export default function GuardianError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <ErrorState
        title="Failed to load Guardian approvals"
        message={error.message || "Unable to fetch approval data."}
        retry={unstable_retry}
      />
    </div>
  )
}
