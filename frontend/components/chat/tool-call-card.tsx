"use client"

import { useState } from "react"
import { Loader2, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ToolCallEntry } from "@/lib/types/api"

interface ToolCallCardProps {
  toolCall: ToolCallEntry
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="my-1 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs">
      <div className="flex items-center gap-2">
        {toolCall.status === "pending" ? (
          <Loader2 className="size-3 shrink-0 animate-spin text-muted-foreground" />
        ) : (
          <CheckCircle2 className="size-3 shrink-0 text-green-500" />
        )}
        <span className={cn("flex-1", toolCall.status === "resolved" && "text-foreground")}>
          {toolCall.status === "pending" ? toolCall.label : toolCall.resultLabel ?? "Done"}
        </span>
        {toolCall.status === "resolved" && toolCall.result && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
          </button>
        )}
      </div>
      {expanded && toolCall.result && (
        <pre className="mt-2 max-h-48 overflow-auto rounded bg-background p-2 text-[10px] leading-relaxed">
          {(() => {
            try {
              return JSON.stringify(JSON.parse(toolCall.result), null, 2)
            } catch {
              return toolCall.result
            }
          })()}
        </pre>
      )}
    </div>
  )
}
