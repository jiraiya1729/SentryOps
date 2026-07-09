"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { streamEvents, type StreamEventsParams } from "@/lib/api/events"
import type { K8sEvent } from "@/lib/types/api"

interface UseEventStreamOptions extends StreamEventsParams {
  enabled: boolean
}

interface UseEventStreamReturn {
  newEvents: K8sEvent[]
  newEventKeys: Set<string>
  isConnected: boolean
  clearNewEvents: () => void
}

function eventKey(e: K8sEvent): string {
  return `${e.namespace}/${e.name}/${e.timestamp}`
}

export function useEventStream({
  enabled,
  ...params
}: UseEventStreamOptions): UseEventStreamReturn {
  const [newEvents, setNewEvents] = useState<K8sEvent[]>([])
  const [newEventKeys, setNewEventKeys] = useState<Set<string>>(new Set())
  const [isConnected, setIsConnected] = useState(false)
  const seenKeysRef = useRef<Set<string>>(new Set())

  const clearNewEvents = useCallback(() => {
    setNewEvents([])
    setNewEventKeys(new Set())
    seenKeysRef.current = new Set()
  }, [])

  useEffect(() => {
    if (!enabled) return

    seenKeysRef.current = new Set()

    const cleanup = streamEvents(
      params,
      (event) => {
        const key = eventKey(event)
        if (seenKeysRef.current.has(key)) return
        seenKeysRef.current.add(key)
        setNewEvents((prev) => [event, ...prev])
        setNewEventKeys((prev) => new Set([...prev, key]))
      },
      () => setIsConnected(true),
      () => setIsConnected(false)
    )

    return () => {
      cleanup()
      setIsConnected(false)
      setNewEvents([])
      setNewEventKeys(new Set())
      seenKeysRef.current = new Set()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, params.namespace, params.event_type, params.since])

  return { newEvents, newEventKeys, isConnected, clearNewEvents }
}
