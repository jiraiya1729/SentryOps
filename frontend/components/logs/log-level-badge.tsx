"use client"

import { cn } from "@/lib/utils"
import type { LogEntry } from "@/lib/types/api"

type LogLevel = LogEntry["log_level"]

const levelStyles: Record<LogLevel, string> = {
  FATAL: "bg-destructive/20 text-destructive border-destructive/30",
  ERROR: "bg-destructive/10 text-destructive border-destructive/20",
  WARN: "bg-warning/10 text-warning border-warning/20",
  INFO: "bg-primary/10 text-primary border-primary/20",
  DEBUG: "bg-muted text-muted-foreground border-border",
  TRACE: "bg-muted text-muted-foreground border-border",
  UNKNOWN: "bg-muted text-muted-foreground border-border",
}

export const levelBarColors: Record<string, string> = {
  FATAL: "bg-destructive",
  ERROR: "bg-destructive",
  WARN: "bg-warning",
  INFO: "bg-primary",
  DEBUG: "bg-muted-foreground/50",
  TRACE: "bg-muted-foreground/30",
  UNKNOWN: "bg-muted-foreground/30",
}

interface LogLevelBadgeProps {
  level: LogLevel
  className?: string
}

export function LogLevelBadge({ level, className }: LogLevelBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase leading-none",
        levelStyles[level],
        className
      )}
    >
      {level}
    </span>
  )
}
