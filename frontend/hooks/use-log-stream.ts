"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import type { LogEntry, StreamLogEntry, WsLogMessage } from "@/lib/types/api"

interface UseLogStreamOptions {
  enabled: boolean
  namespace?: string
  pod?: string
  level?: string
  maxBufferSize?: number
}

interface UseLogStreamReturn {
  logs: LogEntry[]
  isConnected: boolean
  droppedCount: number
  linesPerSecond: number
  clearLogs: () => void
}

const WS_BASE = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws")
  : "ws://localhost:8000"

const MAX_RECONNECT_DELAY = 30000
const BASE_RECONNECT_DELAY = 1000
const FLUSH_INTERVAL = 100
const RATE_UPDATE_INTERVAL = 500

function buildWsUrl(options: UseLogStreamOptions): string {
  const params = new URLSearchParams()
  if (options.namespace) params.set("namespace", options.namespace)
  if (options.pod) params.set("pod", options.pod)
  if (options.level) params.set("level", options.level)
  const qs = params.toString()
  return `${WS_BASE}/ws/logs${qs ? `?${qs}` : ""}`
}

function streamEntryToLogEntry(entry: StreamLogEntry): LogEntry {
  return {
    ...entry,
    node_name: "",
    parsed_fields: {},
  }
}

export function useLogStream({
  enabled,
  namespace,
  pod,
  level,
  maxBufferSize = 1000,
}: UseLogStreamOptions): UseLogStreamReturn {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [droppedCount, setDroppedCount] = useState(0)
  const [linesPerSecond, setLinesPerSecond] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const rateTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const attemptRef = useRef(0)
  const bufferRef = useRef<LogEntry[]>([])
  const messageTimestamps = useRef<number[]>([])
  const enabledRef = useRef(enabled)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  const clearLogs = useCallback(() => {
    setLogs([])
    bufferRef.current = []
    setDroppedCount(0)
    messageTimestamps.current = []
    setLinesPerSecond(0)
  }, [])

  useEffect(() => {
    if (!enabled) return

    bufferRef.current = []
    messageTimestamps.current = []
    attemptRef.current = 0

    function connect() {
      if (!enabledRef.current) return

      const url = buildWsUrl({ enabled, namespace, pod, level })
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        attemptRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg: WsLogMessage = JSON.parse(event.data)

          if (msg.type === "log") {
            const entry = streamEntryToLogEntry(msg.data)
            bufferRef.current.push(entry)
            if (bufferRef.current.length > maxBufferSize) {
              bufferRef.current = bufferRef.current.slice(-maxBufferSize)
            }
            messageTimestamps.current.push(Date.now())
          } else if (msg.type === "dropped") {
            setDroppedCount((prev) => prev + msg.count)
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null
        scheduleReconnect()
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    function scheduleReconnect() {
      if (!enabledRef.current) return
      const delay = Math.min(
        BASE_RECONNECT_DELAY * Math.pow(2, attemptRef.current),
        MAX_RECONNECT_DELAY
      )
      attemptRef.current += 1
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    const flushTimer = setInterval(() => {
      if (bufferRef.current.length > 0) {
        setLogs([...bufferRef.current])
      }
    }, FLUSH_INTERVAL)
    flushTimerRef.current = flushTimer

    const rateTimer = setInterval(() => {
      const now = Date.now()
      const oneSecondAgo = now - 1000
      messageTimestamps.current = messageTimestamps.current.filter(
        (t) => t > oneSecondAgo
      )
      setLinesPerSecond(messageTimestamps.current.length)
    }, RATE_UPDATE_INTERVAL)
    rateTimerRef.current = rateTimer

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      clearInterval(flushTimer)
      clearInterval(rateTimer)
      flushTimerRef.current = null
      rateTimerRef.current = null
      setIsConnected(false)
      setLogs([])
      setDroppedCount(0)
      setLinesPerSecond(0)
    }
  }, [enabled, namespace, pod, level, maxBufferSize])

  return { logs, isConnected, droppedCount, linesPerSecond, clearLogs }
}
