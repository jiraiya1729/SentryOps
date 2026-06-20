"use client"

import { type ColumnDef } from "@tanstack/react-table"
import Link from "next/link"
import type { Pod } from "@/lib/types/api"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"

const columns: ColumnDef<Pod, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        href={`/cluster/pods/${row.original.namespace}/${row.original.name}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "namespace",
    header: "Namespace",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.namespace}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
    filterFn: (row, id, filterValue) => {
      if (!filterValue) return true
      return row.getValue<string>(id).toLowerCase() === filterValue.toLowerCase()
    },
  },
  {
    accessorKey: "ready",
    header: "Ready",
  },
  {
    accessorKey: "restarts",
    header: "Restarts",
    cell: ({ row }) => {
      const restarts = row.original.restarts
      return (
        <span className={restarts > 5 ? "text-destructive font-medium" : ""}>
          {restarts}
        </span>
      )
    },
  },
  {
    accessorKey: "node",
    header: "Node",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-xs">
        {row.original.node ?? "—"}
      </span>
    ),
  },
]

interface PodsTableProps {
  data: Pod[]
}

export function PodsTable({ data }: PodsTableProps) {
  return (
    <DataTable
      columns={columns}
      data={data}
      searchKey="name"
      searchPlaceholder="Search pods..."
      filterKey="status"
      filterOptions={["Running", "Pending", "Failed", "CrashLoopBackOff"]}
    />
  )
}
