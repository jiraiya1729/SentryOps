"use client"

import { useEffect, useRef } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/lib/types/api"
import { ToolCallCard } from "./tool-call-card"

interface ChatMessagesProps {
  messages: ChatMessage[]
  isStreaming: boolean
  suggestedPrompts: string[]
  onPromptClick: (prompt: string) => void
}

export function ChatMessages({
  messages,
  isStreaming,
  suggestedPrompts,
  onPromptClick,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-6">
        <p className="text-xs text-muted-foreground">Ask anything about your cluster</p>
        <div className="flex flex-wrap justify-center gap-2">
          {suggestedPrompts.map(prompt => (
            <button
              key={prompt}
              onClick={() => onPromptClick(prompt)}
              className="rounded-full border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    )
  }

  const lastIdx = messages.length - 1

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      {messages.map((msg, idx) => {
        const isLast = idx === lastIdx
        const showCursor = isLast && isStreaming && msg.role === "assistant"

        return (
          <div
            key={msg.id}
            className={cn(
              "flex flex-col gap-1",
              msg.role === "user" ? "items-end" : "items-start"
            )}
          >
            {msg.role === "user" ? (
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
                {msg.content}
              </div>
            ) : (
              <div className="w-full">
                {(msg.toolCalls ?? []).map(tc => (
                  <ToolCallCard key={tc.id} toolCall={tc} />
                ))}
                {msg.content && (
                  <div className="prose prose-sm prose-invert max-w-none text-sm leading-relaxed [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:text-xs">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
                {showCursor && (
                  <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-foreground" />
                )}
              </div>
            )}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
