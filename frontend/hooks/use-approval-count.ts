"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { getApprovalCount } from "@/lib/api/guardian"

export function useApprovalCount() {
  const [count, setCount] = useState(0)
  const previousCountRef = useRef(0)
  const [hasNew, setHasNew] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await getApprovalCount()
      if (data.count > previousCountRef.current) {
        setHasNew(true)
      }
      previousCountRef.current = data.count
      setCount(data.count)
    } catch {
      // silently ignore polling failures
    }
  }, [])

  const clearNew = useCallback(() => setHasNew(false), [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 10_000)
    return () => clearInterval(interval)
  }, [refresh])

  return { count, hasNew, clearNew, refresh }
}
