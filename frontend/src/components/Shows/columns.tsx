// TODO: Validate
import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import type { ShowPublic } from "@/client"
import { DateCell, TruncatedCell } from "@/components/Common/TableCells"

import { ShowActionsMenu } from "./ActionsMenu"

export type ShowTableData = ShowPublic & { pending?: boolean }

export const showColumns: ColumnDef<ShowTableData>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) =>
      row.original.pending ? (
        <span className="font-medium text-primary block max-w-48 whitespace-normal wrap-break-word">
          {row.original.name || `No Name (${row.original.key})`}
        </span>
      ) : (
        <Link
          to="/show/$showKey"
          params={{ showKey: row.original.id }}
          className="font-medium text-primary hover:underline block max-w-48 whitespace-normal wrap-break-word"
        >
          {row.original.name || `No Name (${row.original.key})`}
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
    cell: ({ row }) => <TruncatedCell value={row.original.description} />,
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
        {row.original.pending ? null : <ShowActionsMenu show={row.original} />}
      </div>
    ),
  },
]
