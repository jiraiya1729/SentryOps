"use client"

interface PayloadEntry {
  dataKey?: string | number
  value?: number
  color?: string
}

interface ChartTooltipProps {
  active?: boolean
  payload?: PayloadEntry[]
  label?: string
  unit?: string
  formatValue?: (value: number) => string
}

export function ChartTooltip({ active, payload, label, unit, formatValue }: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  const time = new Date(label || "").toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })

  return (
    <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
      <p className="text-xs text-muted-foreground mb-2">{time}</p>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={String(entry.dataKey)} className="flex items-center gap-2 text-xs">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-muted-foreground">{String(entry.dataKey)}:</span>
            <span className="font-medium text-foreground">
              {formatValue && entry.value != null ? formatValue(entry.value) : entry.value}
              {unit && ` ${unit}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
