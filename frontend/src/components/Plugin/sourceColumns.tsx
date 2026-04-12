// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import DeleteSource from "./DeleteSource"
import EditSource from "./EditSource"

export interface SourceTableData {
  key: string
  name: string | null
  id: string
  plugin_id: string
  favicon_url: string | null
  image_url: string | null
  data_timestamp: string | null
}

export const sourceColumns: ColumnDef<SourceTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/source/$sourceKey"
        params={{ sourceKey: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name || `No Name (${row.original.key})`}
      </Link>
    ),
  },
  {
    accessorKey: "favicon_url",
    header: "Favicon URL",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.favicon_url ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.image_url ?? "-"}
      </span>
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
        <EditSource source={row.original} />
        <DeleteSource source={row.original} />
      </div>
    ),
  },
]
