"use client"

import { type ColumnDef } from "@tanstack/react-table"
import type { Deployment } from "@/lib/types/api"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"

const columns: ColumnDef<Deployment, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.name}</span>
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
    accessorKey: "ready",
    header: "Ready",
    cell: ({ row }) => (
      <span className="font-mono text-sm">
        {row.original.ready}/{row.original.desired ?? 0}
      </span>
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
    accessorKey: "images",
    header: "Images",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-col gap-0.5">
        {row.original.images.map((image, i) => (
          <span key={i} className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">
            {image}
          </span>
        ))}
      </div>
    ),
  },
]

interface DeploymentsTableProps {
  data: Deployment[]
}

export function DeploymentsTable({ data }: DeploymentsTableProps) {
  return (
    <DataTable
      columns={columns}
      data={data}
      searchKey="name"
      searchPlaceholder="Search deployments..."
      filterKey="status"
      filterOptions={["healthy", "unhealthy", "unavailable"]}
    />
  )
}
