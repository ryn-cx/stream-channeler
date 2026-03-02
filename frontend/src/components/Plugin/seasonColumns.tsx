// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"

import DeleteSeason from "./DeleteSeason"
import EditSeason from "./EditSeason"

export interface SeasonTableData {
  key: string
  name: string | null
  id: string
  show_id: string
  season_number: number | null
  url: string | null
  image_url: string | null
  sort_order: number | null
  data_timestamp: string | null
}

export const seasonColumns: ColumnDef<SeasonTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to="/season/$seasonKey"
        params={{ seasonKey: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name || row.original.id}
      </Link>
    ),
  },
  {
    accessorKey: "season_number",
    header: "Season #",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.season_number ?? "-"}
      </span>
    ),
  },
  {
    accessorKey: "sort_order",
    header: "Sort Order",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.sort_order ?? "-"}
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
        <EditSeason season={row.original} />
        <DeleteSeason season={row.original} />
      </div>
    ),
  },
]
