import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import type { SeasonOutput } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"

import { SeasonActionsMenu } from "./ActionsMenu"

export type SeasonTableData = SeasonOutput & { pending?: boolean }

export const seasonColumns: ColumnDef<SeasonTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="font-medium text-muted-foreground">
          {row.original.name || `No Name (${row.original.key})`}
        </span>
      ) : (
        <Link
          to="/season/$seasonKey"
          params={{ seasonKey: row.original.id }}
          className="font-medium text-primary hover:underline"
        >
          {row.original.name || `No Name (${row.original.key})`}
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
    cell: ({ row }) => <TruncatedCell value={row.original.url} />,
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => <TruncatedCell value={row.original.image_url} />,
  },
  {
    accessorKey: "data_timestamp",
    header: "Data Timestamp",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.data_timestamp} />,
  },
  {
    accessorKey: "update_at",
    header: "Update At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.update_at} />,
  },
  {
    accessorKey: "deleted_at",
    header: "Deleted At",
    meta: { filterVariant: "dateRange" },
    cell: ({ row }) => <DateCell value={row.original.deleted_at} />,
  },
  {
    accessorKey: "extra",
    header: "Extra",
    cell: ({ row }) => <TruncatedCell value={row.original.extra} />,
  },
  {
    accessorKey: "key",
    header: "Key",
    cell: ({ row }) => <TruncatedCell value={row.original.key} />,
  },
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <TruncatedCell value={row.original.id} />,
  },
  {
    id: "actions",
    enableSorting: false,
    enableColumnFilter: false,
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        {row.original.pending ? null : (
          <SeasonActionsMenu season={row.original} />
        )}
      </div>
    ),
  },
]
