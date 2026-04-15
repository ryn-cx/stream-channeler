// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import { cn } from "@/lib/utils"

import DeletePlugin from "./DeletePlugin"
import EditPlugin from "./EditPlugin"

export interface PluginTableData {
  key: string
  name: string | null
  version: string | null
  id: string
  user_id: string | null
  data_timestamp: string | null
  deleted_at: string | null
  public: boolean
}

export const columns: ColumnDef<PluginTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/plugin/$pluginId"
        params={{ pluginId: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name || `No Name (${row.original.key})`}
      </Link>
    ),
  },
  {
    accessorKey: "data_timestamp",
    header: "Data Timestamp",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.data_timestamp
          ? new Date(row.original.data_timestamp).toLocaleString()
          : "-"}
      </span>
    ),
  },
  {
    accessorKey: "deleted_at",
    header: "Deleted At",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.deleted_at
          ? new Date(row.original.deleted_at).toLocaleString()
          : "-"}
      </span>
    ),
  },
  {
    accessorFn: (row) => (row.public ? "Public" : "Private"),
    id: "public",
    header: "Visibility",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 rounded-full",
            row.original.public ? "bg-green-500" : "bg-gray-400",
          )}
        />
        <span className={row.original.public ? "" : "text-muted-foreground"}>
          {row.original.public ? "Public" : "Private"}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.original.key}
      </span>
    ),
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.original.id}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    enableHiding: false,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <EditPlugin plugin={row.original} />
        <DeletePlugin plugin={row.original} />
      </div>
    ),
  },
]
