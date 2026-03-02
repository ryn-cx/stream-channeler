// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import DeleteShow from "./DeleteShow"
import EditShow from "./EditShow"

export interface ShowTableData {
  key: string
  name: string | null
  id: string
  source_id: string
  media_type: string | null
  description: string | null
  url: string | null
  image_url: string | null
  data_timestamp: string | null
}

export const showColumns: ColumnDef<ShowTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/show/$showKey"
        params={{ showKey: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name || row.original.id}
      </Link>
    ),
  },
  {
    accessorKey: "media_type",
    header: "Media Type",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.media_type ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.description ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "url",
    header: "URL",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm truncate max-w-48 block">
        {row.original.url ?? "-"}
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
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    enableHiding: false,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <EditShow show={row.original} />
        <DeleteShow show={row.original} />
      </div>
    ),
  },
]
