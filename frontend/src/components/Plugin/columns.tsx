// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import DeletePlugin from "./DeletePlugin"
import EditPlugin from "./EditPlugin"

export interface PluginTableData {
  key: string
  name: string | null
  id: string
  user_id: string | null
  data_timestamp: string | null
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
        {row.original.name || `No Name (${row.original.id.split("-")[0]})`}
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
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.original.key}
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
