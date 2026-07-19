"use client"

import Link from "next/link"
import type { ColumnDef } from "@tanstack/react-table"
import type { ServiceStats } from "@/lib/types/api"
import { DataTable } from "@/components/shared/data-table"
import { formatDuration, getServiceColor } from "@/lib/traces-utils"

function ErrorRateCell({ rate }: { rate: number }) {
  const pct = (rate * 100).toFixed(1)
  const color =
    rate > 0.1
      ? "text-destructive"
      : rate > 0.05
      ? "text-orange-400"
      : "text-success"
  return <span className={`text-sm font-medium ${color}`}>{pct}%</span>
}

const columns: ColumnDef<ServiceStats>[] = [
  {
    accessorKey: "service_name",
    header: "Service",
    cell: ({ row }) => (
      <Link
        href={`/cluster/traces?service=${encodeURIComponent(row.original.service_name)}`}
        className="flex items-center gap-2 hover:underline"
      >
        <span
          className="h-2.5 w-2.5 rounded-full shrink-0"
          style={{ backgroundColor: getServiceColor(row.original.service_name) }}
        />
        <span className="text-sm font-medium text-primary">{row.original.service_name}</span>
      </Link>
    ),
  },
  {
    accessorKey: "span_count",
    header: "Spans",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.span_count.toLocaleString()}
      </span>
    ),
  },
  {
    accessorKey: "trace_count",
    header: "Traces",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.trace_count.toLocaleString()}
      </span>
    ),
  },
  {
    accessorKey: "error_rate",
    header: "Error Rate",
    cell: ({ row }) => <ErrorRateCell rate={row.original.error_rate} />,
  },
  {
    accessorKey: "avg_duration_ms",
    header: "Avg Latency",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDuration(row.original.avg_duration_ms)}
      </span>
    ),
  },
  {
    accessorKey: "p95_duration_ms",
    header: "P95 Latency",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDuration(row.original.p95_duration_ms)}
      </span>
    ),
  },
]

interface Props {
  services: ServiceStats[]
}

export function ServiceMapTable({ services }: Props) {
  return (
    <DataTable
      columns={columns}
      data={services}
      searchKey="service_name"
      searchPlaceholder="Search services…"
    />
  )
}
