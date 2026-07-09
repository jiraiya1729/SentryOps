"use client"

import { useState, useEffect, useCallback } from "react"
import { streamChat, deleteSession } from "@/lib/api/ai"
import type { ChatMessage, ToolCallEntry } from "@/lib/types/api"

const SESSION_KEY = "sentryops-ai-session-id"

const TOOL_LABELS: Record<string, string> = {
  get_pods: "Searching pods...",
  get_pod_detail: "Fetching pod detail...",
  search_logs: "Searching logs...",
  get_metrics: "Querying metrics...",
  get_events: "Fetching events...",
  get_deployments: "Checking deployments...",
}

function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? `Running ${name}...`
}

function computeResultLabel(resultJson: string, toolName: string): string {
  try {
    const data = JSON.parse(resultJson)
    if ((toolName === "get_pods") && Array.isArray(data.items)) {
      return `Found ${data.items.length} pod${data.items.length !== 1 ? "s" : ""}`
    }
    if (toolName === "get_deployments" && Array.isArray(data.items)) {
      return `Found ${data.items.length} deployment${data.items.length !== 1 ? "s" : ""}`
    }
    if (toolName === "get_events" && Array.isArray(data.events)) {
      return `Found ${data.events.length} event${data.events.length !== 1 ? "s" : ""}`
    }
    if (toolName === "search_logs" && typeof data.total === "number") {
      return `Found ${data.total} log entries`
    }
    return "Done"
  } catch {
    return "Done"
  }
}

export interface UseChatReturn {
  messages: ChatMessage[]
  isStreaming: boolean
  sessionId: string | null
  sendMessage: (text: string) => Promise<void>
  newChat: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY)
    if (stored) setSessionId(stored)
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming || !text.trim()) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text.trim(),
      toolCalls: [],
    }
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      toolCalls: [],
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsStreaming(true)

    try {
      for await (const event of streamChat(text.trim(), sessionId)) {
        if (event.type === "session") {
          setSessionId(event.session_id)
          localStorage.setItem(SESSION_KEY, event.session_id)
        } else if (event.type === "token") {
          setMessages(prev => {
            const copy = [...prev]
            const last = { ...copy[copy.length - 1] }
            last.content = last.content + event.content
            copy[copy.length - 1] = last
            return copy
          })
        } else if (event.type === "tool_call") {
          const entry: ToolCallEntry = {
            id: event.id,
            name: event.name,
            status: "pending",
            label: toolLabel(event.name),
            expanded: false,
          }
          setMessages(prev => {
            const copy = [...prev]
            const last = { ...copy[copy.length - 1] }
            last.toolCalls = [...(last.toolCalls ?? []), entry]
            copy[copy.length - 1] = last
            return copy
          })
        } else if (event.type === "tool_result") {
          setMessages(prev => {
            const copy = [...prev]
            const last = { ...copy[copy.length - 1] }
            last.toolCalls = (last.toolCalls ?? []).map(tc =>
              tc.id === event.id
                ? {
                    ...tc,
                    status: "resolved" as const,
                    result: event.content,
                    resultLabel: computeResultLabel(event.content, tc.name),
                  }
                : tc
            )
            copy[copy.length - 1] = last
            return copy
          })
        } else if (event.type === "done") {
          break
        }
      }
    } finally {
      setIsStreaming(false)
    }
  }, [isStreaming, sessionId])

  const newChat = useCallback(() => {
    if (sessionId) {
      deleteSession(sessionId).catch(() => {})
      localStorage.removeItem(SESSION_KEY)
    }
    setSessionId(null)
    setMessages([])
  }, [sessionId])

  return { messages, isStreaming, sessionId, sendMessage, newChat }
}
