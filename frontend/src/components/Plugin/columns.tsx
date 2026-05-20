// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import type { Visibility } from "@/client"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"

import DeletePlugin from "./DeletePlugin"
import EditPlugin from "./EditPlugin"

export interface PluginTableData {
  key: string
  name: string | null
  version: string | null
  id: string
  user_id: string | null
  data_timestamp: string | null
  update_at: string | null
  deleted_at: string | null
  visibility: Visibility
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
    accessorKey: "update_at",
    header: "Update At",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.update_at
          ? new Date(row.original.update_at).toLocaleString()
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
    accessorFn: (row) => visibilityLabel(row.visibility),
    id: "visibility",
    header: "Visibility",
    cell: ({ row }) => {
      const visibility = row.original.visibility
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              visibilityDotClass(visibility),
            )}
          />
          <span
            className={visibility === "private" ? "text-muted-foreground" : ""}
          >
            {visibilityLabel(visibility)}
          </span>
        </div>
      )
    },
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
