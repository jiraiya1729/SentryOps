"use client"

import { type ColumnDef } from "@tanstack/react-table"
import type { Node } from "@/lib/types/api"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { Server } from "lucide-react"

const columns: ColumnDef<Node, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Server className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-medium">{row.original.name}</span>
      </div>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

interface NodesTableProps {
  data: Node[]
}

export function NodesTable({ data }: NodesTableProps) {
  return (
    <DataTable
      columns={columns}
      data={data}
      searchKey="name"
      searchPlaceholder="Search nodes..."
    />
  )
}
