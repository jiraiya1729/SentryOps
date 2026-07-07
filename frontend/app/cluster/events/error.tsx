"use client"

import { ErrorState } from "@/components/shared/error-state"

export default function EventsError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <ErrorState
        title="Failed to load events"
        message={error.message || "Unable to fetch cluster events."}
        retry={unstable_retry}
      />
    </div>
  )
}
