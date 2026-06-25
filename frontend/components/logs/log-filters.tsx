"use client"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Search, ChevronDown, RefreshCw, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

const LOG_LEVELS = ["ERROR", "WARN", "INFO", "DEBUG"] as const

const TIME_RANGES = [
  { label: "15m", value: 15 },
  { label: "1h", value: 60 },
  { label: "6h", value: 360 },
  { label: "24h", value: 1440 },
  { label: "7d", value: 10080 },
] as const

interface LogFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  namespace: string
  onNamespaceChange: (value: string) => void
  pod: string
  onPodChange: (value: string) => void
  levels: string[]
  onLevelsChange: (levels: string[]) => void
  timeRange: number | null
  onTimeRangeChange: (minutes: number | null) => void
  autoRefresh: boolean
  onAutoRefreshToggle: () => void
  lastUpdatedText: string | null
  namespaceOptions: string[]
  liveMode: boolean
  onLiveModeToggle: () => void
  isConnected?: boolean
  linesPerSecond?: number
}

export function LogFilters({
  search,
  onSearchChange,
  namespace,
  onNamespaceChange,
  pod,
  onPodChange,
  levels,
  onLevelsChange,
  timeRange,
  onTimeRangeChange,
  autoRefresh,
  onAutoRefreshToggle,
  lastUpdatedText,
  namespaceOptions,
  liveMode,
  onLiveModeToggle,
  isConnected,
  linesPerSecond,
}: LogFiltersProps) {

  function toggleLevel(level: string) {
    if (levels.includes(level)) {
      onLevelsChange(levels.filter((l) => l !== level))
    } else {
      onLevelsChange([...levels, level])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search logs..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 h-8 text-sm bg-background border-border"
          />
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 h-8 text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors">
            <span className="truncate max-w-24">
              {namespace || "Namespace"}
            </span>
            <ChevronDown className="h-3 w-3 shrink-0" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => onNamespaceChange("")}>
              All namespaces
            </DropdownMenuItem>
            {namespaceOptions.map((ns) => (
              <DropdownMenuItem key={ns} onClick={() => onNamespaceChange(ns)}>
                {ns}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="relative min-w-32 max-w-48">
          <Input
            placeholder="Pod name..."
            value={pod}
            onChange={(e) => onPodChange(e.target.value)}
            className="h-8 text-xs bg-background border-border"
          />
        </div>

        <div className="flex items-center gap-1">
          {LOG_LEVELS.map((level) => (
            <Button
              key={level}
              variant={levels.includes(level) ? "default" : "outline"}
              size="xs"
              onClick={() => toggleLevel(level)}
              className={cn(
                "text-[10px] h-7 px-2 font-semibold",
                levels.includes(level) && level === "ERROR" && "bg-destructive hover:bg-destructive/90",
                levels.includes(level) && level === "WARN" && "bg-warning hover:bg-warning/90 text-warning-foreground",
                levels.includes(level) && level === "INFO" && "bg-primary hover:bg-primary/90",
                levels.includes(level) && level === "DEBUG" && "bg-muted-foreground hover:bg-muted-foreground/90"
              )}
            >
              {level}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {!liveMode && (
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-muted-foreground" />
            {TIME_RANGES.map((range) => (
              <Button
                key={range.value}
                variant={timeRange === range.value ? "secondary" : "ghost"}
                size="xs"
                className="text-[11px] h-6 px-2"
                onClick={() =>
                  onTimeRangeChange(timeRange === range.value ? null : range.value)
                }
              >
                {range.label}
              </Button>
            ))}
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          {liveMode && isConnected && linesPerSecond !== undefined && (
            <span className="text-[11px] text-muted-foreground">
              Streaming... {linesPerSecond} lines/sec
            </span>
          )}

          <Button
            variant={liveMode ? "default" : "ghost"}
            size="xs"
            className={cn(
              "h-6 gap-1.5 text-[11px]",
              liveMode && "bg-green-600 hover:bg-green-700 text-white"
            )}
            onClick={onLiveModeToggle}
          >
            {liveMode && isConnected && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
            )}
            Live
          </Button>

          {!liveMode && (
            <>
              {lastUpdatedText && (
                <span className="text-[11px] text-muted-foreground">
                  Updated {lastUpdatedText}
                </span>
              )}
              <Button
                variant={autoRefresh ? "secondary" : "ghost"}
                size="xs"
                className="h-6 gap-1 text-[11px]"
                onClick={onAutoRefreshToggle}
              >
                <RefreshCw
                  className={cn("h-3 w-3", autoRefresh && "animate-spin")}
                />
                Auto
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
