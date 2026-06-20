"use client"

import { ErrorState } from "@/components/shared/error-state"

export default function ClusterError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <ErrorState
        title="Failed to load cluster data"
        message={error.message || "Unable to connect to the cluster API."}
        retry={unstable_retry}
      />
    </div>
  )
}
