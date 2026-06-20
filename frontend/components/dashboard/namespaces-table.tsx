"use client"

import { type ColumnDef } from "@tanstack/react-table"
import type { Namespace } from "@/lib/types/api"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"

const columns: ColumnDef<Namespace, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.name}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "pod_count",
    header: "Pods",
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.original.pod_count}</span>
    ),
  },
]

interface NamespacesTableProps {
  data: Namespace[]
}

export function NamespacesTable({ data }: NamespacesTableProps) {
  return (
    <DataTable
      columns={columns}
      data={data}
      searchKey="name"
      searchPlaceholder="Search namespaces..."
    />
  )
}
