// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"

import { SourceActionsMenu } from "./SourceActionsMenu"

export interface SourceTableData {
  key: string
  name: string | null
  id: string
  plugin_id: string
  favicon_url: string | null
  image_url: string | null
  data_timestamp: string | null
  update_at: string | null
  pending?: boolean
}

export const sourceColumns: ColumnDef<SourceTableData>[] = [
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
    cell: ({ row }) => <TruncatedCell value={row.original.favicon_url} />,
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
          <SourceActionsMenu source={row.original} />
        )}
      </div>
    ),
  },
]
